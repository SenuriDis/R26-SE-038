"""
tests/test_ml_report_reader.py
─────────────────────────────────
Regression tests for src/utils/ml_report_reader.py:

1. EnrichedSegment.effective_test_types() — merges the tier-level default
   test types with Component 2's own per-function recommendation.
   Previously `recommended_test_types` was parsed out of the ML report but
   never actually passed to Agent 1 — the pipeline used the generic tier
   default only, silently discarding Component 2's specific guidance
   (e.g. "boundary_tests", "typical_inputs").

2. MLReportReader preferring Component 2's own `recommended_test_depth`
   per function over the coarse HIGH/MEDIUM/LOW tier default, falling back
   to the tier default only when it's missing or unrecognised.

Run with: python -m pytest tests/test_ml_report_reader.py -v
"""

import json

from src.utils.ml_report_reader import EnrichedSegment, MLReportReader
from src.models.schemas import HighRiskSegment


def _make_segment() -> HighRiskSegment:
    return HighRiskSegment(
        segment_id="medium-process_transaction-1",
        file_path="src/payment.py",
        function_name="process_transaction",
        source_code="def process_transaction(): pass",
        risk_score=0.4294,
        start_line=45,
        end_line=78,
        cyclomatic_complexity=None,
    )


def test_effective_test_types_merges_tier_and_ml_recommendations():
    """Component 2's own test_types must be folded in, not discarded."""
    enriched = EnrichedSegment(
        segment=_make_segment(),
        risk_level="MEDIUM",
        test_depth="boundary",
        min_test_cases=6,
        test_types=["normal", "edge", "boundary"],          # tier default
        explanation_text="Risk driven by bug history",
        top_risk_factors=[],
        recommended_test_types=["boundary_tests", "typical_inputs"],  # from ML report
        confidence=0.4805,
    )

    result = enriched.effective_test_types()

    # Tier defaults are kept (baseline for Agent 1's category vocabulary)...
    assert "normal" in result
    assert "edge" in result
    assert "boundary" in result
    # ...and Component 2's own recommendation is no longer dropped.
    assert "boundary_tests" in result
    assert "typical_inputs" in result


def test_effective_test_types_deduplicates_overlap():
    """Overlapping entries between tier default and ML recommendation
    should not be duplicated in the merged list."""
    enriched = EnrichedSegment(
        segment=_make_segment(),
        risk_level="LOW",
        test_depth="basic",
        min_test_cases=3,
        test_types=["normal"],
        explanation_text="",
        top_risk_factors=[],
        recommended_test_types=["normal", "happy_path"],
        confidence=1.0,
    )

    result = enriched.effective_test_types()

    assert result.count("normal") == 1
    assert "happy_path" in result


# ── MLReportReader.load() — recommended_test_depth precedence ────────────────

def _write_repo(tmp_path):
    """A minimal repo containing the one function these tests reference."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "payment.py").write_text(
        "def process_transaction():\n    pass\n",
        encoding="utf-8",
    )
    return tmp_path


def _write_report(tmp_path, medium_function: dict):
    report = {
        "project": "test-project",
        "summary": {},
        "tier_breakdown": {
            "HIGH": {"description": "", "functions": []},
            "MEDIUM": {"description": "", "functions": [medium_function]},
            "LOW": {"description": "", "functions": []},
        },
        "ranked_functions": [],
    }
    report_path = tmp_path / "ml_output.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    return report_path


def _base_function(**overrides) -> dict:
    func = {
        "function_name": "process_transaction",
        "file_path": "src/payment.py",
        "start_line": 1,
        "end_line": 2,
        "risk_score": 0.5,
        "confidence": 0.8,
        "priority_rank": 1,
        "explanation_text": "",
        "top_risk_factors": [],
        "test_types": ["boundary_tests"],
    }
    func.update(overrides)
    return func


def test_load_prefers_component2_recommended_test_depth(tmp_path):
    """A MEDIUM-tier function explicitly recommended for exhaustive
    testing should get the exhaustive profile, not MEDIUM's usual
    boundary default -- Component 2's per-function call wins."""
    repo = _write_repo(tmp_path)
    report_path = _write_report(
        tmp_path, _base_function(recommended_test_depth="exhaustive")
    )

    reader = MLReportReader(str(report_path), str(repo))
    segments = reader.load(min_risk_level="LOW")

    assert len(segments) == 1
    assert segments[0].test_depth == "exhaustive"
    assert segments[0].min_test_cases == 10


def test_load_falls_back_to_tier_default_when_depth_missing(tmp_path):
    """No recommended_test_depth field at all -> use the MEDIUM tier
    default (boundary)."""
    repo = _write_repo(tmp_path)
    report_path = _write_report(tmp_path, _base_function())

    reader = MLReportReader(str(report_path), str(repo))
    segments = reader.load(min_risk_level="LOW")

    assert segments[0].test_depth == "boundary"
    assert segments[0].min_test_cases == 6


def test_load_falls_back_when_depth_unrecognised(tmp_path):
    """An unrecognised recommended_test_depth value must not crash the
    pipeline -- it should fall back to the tier default instead."""
    repo = _write_repo(tmp_path)
    report_path = _write_report(
        tmp_path,
        _base_function(recommended_test_depth="some_future_depth"),
    )

    reader = MLReportReader(str(report_path), str(repo))
    segments = reader.load(min_risk_level="LOW")

    assert segments[0].test_depth == "boundary"
