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
 

