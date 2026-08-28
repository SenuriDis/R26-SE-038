"""
src/utils/ml_report_reader.py
──────────────────────────────
Reads Component 2's ML risk report JSON and converts it into
HighRiskSegment objects that the pipeline can process.

Also handles:
- Tier-based test depth (HIGH/MEDIUM/LOW)
- Source code extraction using CodeExtractor
- Risk factor injection for Agent prompts
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass

from src.models.schemas import HighRiskSegment
from src.utils.code_extractor import CodeExtractor

logger = logging.getLogger(__name__)


# ── Test depth configuration per tier ─────────────────────────────────────────

TIER_CONFIG = {
    "HIGH": {
        "description": "Exhaustive testing — all test case types",
        "test_depth": "exhaustive",
        "min_test_cases": 10,
        "test_types": [
            "normal", "edge", "negative", "exception", "boundary"
        ],
    },
    "MEDIUM": {
        "description": "Boundary testing — edge cases and boundaries",
        "test_depth": "boundary",
        "min_test_cases": 6,
        "test_types": [
            "normal", "edge", "boundary"
        ],
    },
    "LOW": {
        "description": "Basic testing — happy path only",
        "test_depth": "basic",
        "min_test_cases": 3,
        "test_types": [
            "normal"
        ],
    },
}


@dataclass
class EnrichedSegment:
    """
    A HighRiskSegment enriched with ML-specific signals
    that get injected into agent prompts.
    """
    segment: HighRiskSegment
    risk_level: str                    # HIGH / MEDIUM / LOW
    test_depth: str                    # exhaustive / boundary / basic
    min_test_cases: int                # minimum number of test cases to generate
    test_types: list[str]              # which categories of tests to write
    explanation_text: str              # human readable risk explanation
    top_risk_factors: list[dict]       # ML feature contributions
    recommended_test_types: list[str]  # from Component 2 directly
    confidence: float                  # ML model confidence

    def effective_test_types(self) -> list[str]:
        """
        Merge the tier-level default test types with Component 2's own
        per-function recommendation.

        `test_types` (from TIER_CONFIG) keeps the generic categories that
        line up with Agent 1's fixed category vocabulary (normal/edge/
        negative/exception), so a segment always gets a sane baseline for
        its risk tier. `recommended_test_types` is Component 2's specific,
        per-function guidance (e.g. "boundary_tests") and used to be
        collected but never actually passed to Agent 1 — this folds it in
        instead of discarding it, without dropping the tier baseline.
        """
        merged = list(self.test_types)
        for t in self.recommended_test_types:
            if t not in merged:
                merged.append(t)
        return merged


class MLReportReader:
    """
    Reads Component 2's JSON output and produces EnrichedSegments
    ready for the pipeline.

    Usage:
        reader = MLReportReader(
            report_path="ml_output.json",
            repository_path="/path/to/repo"
        )
        segments = reader.load(min_risk_level="LOW")
    """

    def __init__(self, report_path: str, repository_path: str):
        self.report_path = Path(report_path)
        self.repository_path = Path(repository_path).resolve()
        self.extractor = CodeExtractor(str(repository_path))

        if not self.report_path.exists():
            raise FileNotFoundError(
                f"ML report not found: {self.report_path}"
            )

    def load(self, min_risk_level: str = "MEDIUM") -> list[EnrichedSegment]:
        """
        Load the ML report and return enriched segments.

        Args:
            min_risk_level: Minimum risk tier to include.
                           "HIGH"   → only HIGH
                           "MEDIUM" → HIGH + MEDIUM
                           "LOW"    → all functions

        Returns:
            List of EnrichedSegment sorted by priority rank
        """
        with open(self.report_path, "r", encoding="utf-8") as f:
            report = json.load(f)

        # Determine which tiers to include
        tier_order = ["HIGH", "MEDIUM", "LOW"]
        min_idx = tier_order.index(min_risk_level)
        included_tiers = tier_order[:min_idx + 1]

        logger.info(
            f"Loading ML report | project={report.get('project', 'unknown')} | "
            f"min_tier={min_risk_level} | tiers={included_tiers}"
        )

        enriched_segments = []

        # Process functions from tier_breakdown
        tier_breakdown = report.get("tier_breakdown", {})

        for tier in included_tiers:
            tier_data = tier_breakdown.get(tier, {})
            functions = tier_data.get("functions", [])

            logger.info(
                f"Tier {tier}: {len(functions)} functions"
            )

            for func in functions:
                enriched = self._process_function(func, tier)
                if enriched:
                    enriched_segments.append(enriched)

        # Sort by priority rank
        enriched_segments.sort(
            key=lambda x: x.segment.risk_score,
            reverse=True
        )

        logger.info(
            f"Loaded {len(enriched_segments)} segments from ML report"
        )

        return enriched_segments

    def _process_function(
        self,
        func: dict,
        tier: str,
    ) -> EnrichedSegment | None:
        """
        Process one function entry from the ML report.
        Extracts source code and builds an EnrichedSegment.
        """
        function_name = func.get("function_name", "")
        file_path = func.get("file_path", "")
        start_line = func.get("start_line", 1)
        end_line = func.get("end_line", 1)
        risk_score = func.get("risk_score", 0.0)
        confidence = func.get("confidence", 1.0)
        explanation = func.get("explanation_text", "")
        risk_factors = func.get("top_risk_factors", [])
        recommended_types = func.get("test_types", ["happy_path"])

        # Extract source code from the repository
        try:
            source_code = self.extractor.extract(
                file_path=file_path,
                function_name=function_name,
                start_line=start_line,
                end_line=end_line,
            )

            if not source_code.strip():
                logger.warning(
                    f"Empty source code for {function_name} in {file_path}. "
                    f"Skipping."
                )
                return None

        except FileNotFoundError as e:
            logger.error(f"Could not extract {function_name}: {e}")
            return None

        # Build segment ID
        segment_id = (
            f"{tier.lower()}-"
            f"{function_name}-"
            f"{func.get('priority_rank', 0)}"
        )

        # Build HighRiskSegment
        segment = HighRiskSegment(
            segment_id=segment_id,
            file_path=file_path,
            function_name=function_name,
            source_code=source_code,
            risk_score=risk_score,
            start_line=start_line,
            end_line=end_line,
            cyclomatic_complexity=None,
        )

        # Get tier config
        config = TIER_CONFIG.get(tier, TIER_CONFIG["LOW"])

        logger.info(
            f"Processed {tier} | {function_name} | "
            f"risk={risk_score:.3f} | depth={config['test_depth']}"
        )

        return EnrichedSegment(
            segment=segment,
            risk_level=tier,
            test_depth=config["test_depth"],
            min_test_cases=config["min_test_cases"],
            test_types=config["test_types"],
            explanation_text=explanation,
            top_risk_factors=risk_factors,
            recommended_test_types=recommended_types,
            confidence=confidence,
        )

    def get_summary(self) -> dict:
        """Return a summary of the ML report."""
        with open(self.report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
        return report.get("summary", {})