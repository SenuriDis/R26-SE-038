# This component convert RAW Ml predictions into final priority list and rankings. This is forwaded to LLM for Test Case generation.
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from models.risk_detector import RiskPrediction, RiskThresholds
 
logger = logging.getLogger(__name__)
 
 
@dataclass
class PrioritizedFunction:
    """
    Final output per function - consumed by Component 3 (LLM Test Generation).
    Serialised as JSON over REST API.
    """
    # Identity
    function_name: str
    file_path: str
    start_line: int
    end_line: int
 
    # Risk scores
    risk_score: float
    risk_level: str           # HIGH / MEDIUM / LOW
    confidence: float
    priority_rank: int
 
    # Top 3 risk factors (for LLM context injection)
    top_risk_factors: List[Dict[str, Any]]
    explanation_text: str
 
    # Test generation guidance for Component 3
    recommended_test_depth: str     # exhaustive / boundary / basic
    test_types: List[str]           # e.g. ["boundary", "negative", "edge_cases"]
 
    # Model breakdown
    ensemble_score: float
    rf_score: float
    xgb_score: float
 
class TestPrioritizer:
    """
    Converts ML predictions into a ranked list ready for Component 3.
    Implements the priority tiers described in the proposal:
      HIGH   → Top 20%  → exhaustive tests (boundary + negative + edge + exception)
      MEDIUM → Next 30% → boundary tests (parameter limits + common inputs)
      LOW    → Bottom 50% → basic tests (happy path only)
    """
 
    TEST_TYPE_MAP = {
        "exhaustive": ["boundary_tests", "negative_tests", "edge_cases", "exception_handling"],
        "boundary":   ["boundary_tests", "typical_inputs"],
        "basic":      ["happy_path"],
    }
 
    def prioritize(
        self,
        predictions: List[RiskPrediction],
        project_name: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Takes model predictions, returns the full prioritization payload
        that Component 3 (LLM) will consume.
        """
        total = len(predictions)
        high_cutoff = max(1, int(total * 0.20))
        medium_cutoff = max(1, int(total * 0.50))
 
        prioritized: List[PrioritizedFunction] = []
 
        for i, pred in enumerate(predictions):   # Already sorted by rank
            test_types = self.TEST_TYPE_MAP.get(pred.recommended_test_depth, ["happy_path"])
 
            pf = PrioritizedFunction(
                function_name=pred.function_name,
                file_path=pred.file_path,
                start_line=pred.start_line,
                end_line=pred.end_line,
                risk_score=round(pred.risk_score, 4),
                risk_level=pred.risk_level,
                confidence=round(pred.confidence, 4),
                priority_rank=pred.priority_rank,
                top_risk_factors=pred.top_risk_factors,
                explanation_text=pred.explanation_text,
                recommended_test_depth=pred.recommended_test_depth,
                test_types=test_types,
                ensemble_score=round(pred.risk_score, 4),
                rf_score=round(pred.model_rf_score, 4),
                xgb_score=round(pred.model_xgb_score, 4),
            )
            prioritized.append(pf)
 
        # Summary statistics
        high_risk = [p for p in prioritized if p.risk_level == "HIGH"]
        medium_risk = [p for p in prioritized if p.risk_level == "MEDIUM"]
        low_risk = [p for p in prioritized if p.risk_level == "LOW"]
 
        avg_score = sum(p.risk_score for p in prioritized) / max(len(prioritized), 1)
 
        payload = {
            "project": project_name,
            "summary": {
                "total_functions": total,
                "high_risk_count": len(high_risk),
                "medium_risk_count": len(medium_risk),
                "low_risk_count": len(low_risk),
                "average_risk_score": round(avg_score, 4),
                "high_risk_pct": round(len(high_risk) / max(total, 1) * 100, 1),
            },
            "tier_breakdown": {
                "HIGH": {
                    "description": "Top 20% — exhaustive tests recommended",
                    "functions": [asdict(p) for p in high_risk],
                },
                "MEDIUM": {
                    "description": "Next 30% — boundary tests recommended",
                    "functions": [asdict(p) for p in medium_risk],
                },
                "LOW": {
                    "description": "Bottom 50% — basic happy-path tests",
                    "functions": [asdict(p) for p in low_risk],
                },
            },
            # Flat ranked list (for Component 3 sequential processing)
            "ranked_functions": [asdict(p) for p in prioritized],
        }
 
        logger.info(
            f"Prioritization complete: {len(high_risk)} HIGH, "
            f"{len(medium_risk)} MEDIUM, {len(low_risk)} LOW"
        )
        return payload
 
    def export_json(self, payload: Dict, path: str) -> None:
        """Write prioritization payload to JSON file."""
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)
        logger.info(f"Prioritization payload exported to {path}")
 
    @staticmethod
    def print_summary(payload: Dict) -> None:
        """Pretty-print risk summary to console."""
        s = payload["summary"]
        print("\n" + "=" * 60)
        print(f"  ML RISK ANALYSIS - {payload['project']}")
        print("=" * 60)
        print(f"  Functions analysed : {s['total_functions']}")
        print(f"  HIGH risk          : {s['high_risk_count']}  ({s['high_risk_pct']}%)")
        print(f"  MEDIUM risk        : {s['medium_risk_count']}")
        print(f"  LOW risk           : {s['low_risk_count']}")
        print(f"  Avg risk score     : {s['average_risk_score']:.3f}")
        print("=" * 60)
 
        print("\n  TOP HIGH-RISK FUNCTIONS:")
        for fn in payload["tier_breakdown"]["HIGH"]["functions"][:5]:
            print(
                f"  [{fn['priority_rank']:>3}] {fn['function_name']:<35} "
                f"score={fn['risk_score']:.3f}  conf={fn['confidence']:.2f}  "
                f"depth={fn['recommended_test_depth']}"
            )
            print(f"       -> {fn['explanation_text']}")
        print()

