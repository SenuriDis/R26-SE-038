"""
tests/test_ml_report_reader.py
─────────────────────────────────
Regression test for EnrichedSegment.effective_test_types(), which merges
the tier-level default test types with Component 2's own per-function
recommendation. Previously, `recommended_test_types` was parsed out of the
ML report but never actually passed to Agent 1 — the pipeline used the
generic tier default only, silently discarding Component 2's specific
guidance (e.g. "boundary_tests", "typical_inputs").

Run with: python -m pytest tests/test_ml_report_reader.py -v
"""

from src.utils.ml_report_reader import EnrichedSegment
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
