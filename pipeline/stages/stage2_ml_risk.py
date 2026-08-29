"""
Stage 2 -- C2 ML risk detection.

Reads  02_c2_input.json  (BatchPredictRequest shape)
Writes 03_ml_output.json (tier_breakdown shape, what C3 already reads)

C2 is invoked as a subprocess so it runs against its own interpreter and
dependency set. Point at it with --c2-python or the C2_PYTHON env var; the
orchestrator's own interpreter is used when neither is set.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

from pipeline import contracts

RUNNER = Path(__file__).resolve().parent.parent / "runners" / "c2_predict.py"
MODEL_RELATIVE = Path("models") / "saved" / "risk_detector.pkl"


class Stage2Error(RuntimeError):
    """Raised when C2 cannot be run or fails while scoring."""


def resolve_python(explicit: Optional[str] = None) -> str:
    """
    Choose the interpreter to run C2 with.

    Priority: explicit flag, then C2_PYTHON, then a venv sitting inside C2's
    own directory, then whatever is running the orchestrator.
    """
    if explicit:
        return explicit

    from_env = os.environ.get("C2_PYTHON")
    if from_env:
        return from_env

    for candidate in (
        contracts.C2_ROOT.parent / "venv" / "Scripts" / "python.exe",
        contracts.C2_ROOT.parent / "venv" / "bin" / "python",
        contracts.C2_ROOT.parent / ".venv" / "Scripts" / "python.exe",
        contracts.C2_ROOT.parent / ".venv" / "bin" / "python",
    ):
        if candidate.exists():
            return str(candidate)

    return sys.executable


def check_dependencies(python_exe: str) -> Optional[str]:
    """
    Return None when C2's imports are satisfied, else a human-readable reason.

    Checked up front because the alternative is a traceback from deep inside a
    subprocess that looks like a pipeline bug rather than a missing package.
    """
    if not shutil.which(python_exe) and not Path(python_exe).exists():
        return f"interpreter not found: {python_exe}"

    probe = (
        "import numpy, pandas, sklearn, xgboost"
    )
    result = subprocess.run(
        [python_exe, "-c", probe],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        missing = result.stderr.strip().splitlines()[-1] if result.stderr else "unknown"
        return (
            f"{python_exe} cannot import C2's dependencies ({missing}). "
            f"Install them with:\n"
            f"    {python_exe} -m pip install -r "
            f"{contracts.C2_ROOT.parent / 'requirements.txt'}"
        )

    return None


def run(artifact_dir: Path, python_exe: Optional[str] = None) -> Dict:
    """Score stage 1's output with C2's model and write 03_ml_output.json."""
    input_path = artifact_dir / contracts.STAGE1_C2_INPUT
    output_path = artifact_dir / contracts.STAGE2_ML_OUTPUT

    if not input_path.exists():
        raise Stage2Error(
            f"{input_path} is missing -- run stage 1 first."
        )

    interpreter = resolve_python(python_exe)

    problem = check_dependencies(interpreter)
    if problem:
        raise Stage2Error(problem)

    model_path = contracts.C2_ROOT / MODEL_RELATIVE
    if not model_path.exists():
        raise Stage2Error(
            f"C2's trained model is missing at {model_path}. "
            f"Run train.py inside {contracts.C2_ROOT} to produce it."
        )

    # cwd is C2's package root so its `from utils...` / `from models...`
    # imports resolve, and so the runner's relative model paths line up.
    result = subprocess.run(
        [
            interpreter,
            str(RUNNER),
            str(input_path.resolve()),
            str(output_path.resolve()),
            str(MODEL_RELATIVE),
        ],
        cwd=str(contracts.C2_ROOT),
        capture_output=True,
        text=True,
    )

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")

    if result.returncode != 0:
        raise Stage2Error(f"C2 exited with code {result.returncode}.")

    return {
        "ml_output_artifact": str(output_path),
        "interpreter": interpreter,
    }
