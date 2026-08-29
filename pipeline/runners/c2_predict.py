"""
Runs C2's risk model. Executed inside C2's own environment, with C2's
ml_risk_detector/ directory as both cwd and sys.path[0].

    python c2_predict.py <input.json> <output.json> [model_path]

Reads the BatchPredictRequest-shaped artifact from stage 1, writes the
tier_breakdown payload that C3's ml_report_reader.py consumes.

This mirrors the chain in C2's own /predict endpoint, with one deliberate
difference: it loads the *fitted* FeatureEngineer that train.py saves to
models/saved/feature_engineer.pkl. The API builds a bare FeatureEngineer()
instead, which leaves it unfitted -- so it feeds raw, unnormalised features to
a model trained on z-scored ones. See PIPELINE_NOTES.md.
"""

import json
import logging
import pickle
import sys
from pathlib import Path

import numpy as np

from utils.feature_engineering import FeatureEngineer
from models.risk_detector import MLRiskDetector
from models.prioritizer import TestPrioritizer

logging.basicConfig(level=logging.INFO, format="  [C2] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_MODEL = "models/saved/risk_detector.pkl"
FITTED_FE = "models/saved/feature_engineer.pkl"


def load_feature_engineer() -> FeatureEngineer:
    """
    Prefer the FeatureEngineer that training fitted and pickled. Fall back to
    an unfitted one only if that file is missing -- transform() then returns
    raw features, which is what C2's API does today.
    """
    fe_path = Path(FITTED_FE)
    if not fe_path.exists():
        logger.warning(
            "%s not found -- falling back to an UNFITTED FeatureEngineer. "
            "Features will not be normalised and risk scores will be "
            "unreliable. Run train.py to produce it.",
            FITTED_FE,
        )
        return FeatureEngineer()

    with fe_path.open("rb") as handle:
        fe = pickle.load(handle)

    if getattr(fe, "_fit_stats", None) is None:
        logger.warning("%s unpickled but is not fitted.", FITTED_FE)
    else:
        logger.info("Loaded fitted FeatureEngineer from %s", FITTED_FE)

    return fe


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    model_path = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_MODEL

    payload_in = json.loads(input_path.read_text(encoding="utf-8"))
    functions = payload_in.get("functions", [])
    project_name = payload_in.get("project_name", "unnamed_project")

    if not functions:
        logger.error("No functions in %s -- nothing to score.", input_path)
        return 1

    if not Path(model_path).exists():
        logger.error("Model not found at %s. Run C2's train.py first.", model_path)
        return 1

    # C2's own JSON -> CodeMetrics parser, so the field mapping stays C2's
    # responsibility rather than being duplicated here.
    metrics_list = [FeatureEngineer.from_json(fn) for fn in functions]

    fe = load_feature_engineer()
    feature_matrix = np.stack([fe.transform(m) for m in metrics_list])

    detector = MLRiskDetector.load(model_path)

    metadata = [
        {
            "function_name": m.function_name,
            "file_path": m.file_path,
            "start_line": m.start_line,
            "end_line": m.end_line,
        }
        for m in metrics_list
    ]

    predictions = detector.predict_batch(feature_matrix, metadata)
    payload_out = TestPrioritizer().prioritize(predictions, project_name=project_name)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload_out, indent=2), encoding="utf-8")

    summary = payload_out.get("summary", {})
    logger.info(
        "Scored %d functions -> HIGH=%s MEDIUM=%s LOW=%s",
        len(functions),
        summary.get("high_risk_count"),
        summary.get("medium_risk_count"),
        summary.get("low_risk_count"),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
