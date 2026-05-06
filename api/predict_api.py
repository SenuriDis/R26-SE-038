import os
import sys
import logging
import json
import time
from typing import List, Optional, Dict, Any
 
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
 
from utils.feature_engineering import FeatureEngineer, CodeMetrics
from models.risk_detector import MLRiskDetector, RiskPrediction
from models.prioritizer import TestPrioritizer
 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
app = FastAPI(
    title="ML Risk Detector API",
    description="Comp 2— ML-Based High-Risk Code Detection (IT22292872)",
    version="0.5",
)
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
 
_detector: Optional[MLRiskDetector] = None
_feature_engineer: Optional[FeatureEngineer] = None
_prioritizer = TestPrioritizer()
 
MODEL_PATH = os.environ.get("MODEL_PATH", "models/saved/risk_detector.pkl")
 
 
@app.on_event("startup")
async def startup():
    global _detector, _feature_engineer
    if os.path.exists(MODEL_PATH):
        logger.info(f"Loading model from {MODEL_PATH}")
        _detector = MLRiskDetector.load(MODEL_PATH)
        _feature_engineer = FeatureEngineer()
        logger.info("Model loaded successfully.")
    else:
        logger.warning(
            f"No saved model found at {MODEL_PATH}. "
            "Call POST /train to train a new model."
        )
 
 
class FunctionMetricsRequest(BaseModel):
    """
    Single function metric input — mirrors Component 1 output format.
    All fields optional to support partial AST extraction.
    """
    function_name: str = Field(..., example="process_transaction")
    file_path: str = Field(..., example="src/payment.py")
    start_line: int = Field(1, example=45)
    end_line: int = Field(1, example=78)
 
    cyclomatic_complexity: int = Field(1, ge=1, example=18)
    nesting_depth: int = Field(0, ge=0, example=5)
    lines_of_code: int = Field(1, ge=1, example=87)
    fan_in: int = Field(0, ge=0, example=3)
    fan_out: int = Field(0, ge=0, example=12)
    num_parameters: int = Field(0, ge=0, example=4)
    commit_frequency: int = Field(0, ge=0, example=23)
    author_count: int = Field(1, ge=0, example=3)
    bug_history: int = Field(0, ge=0, example=3)
    days_since_last_change: int = Field(999, ge=0, example=7)
    num_return_statements: int = Field(0, ge=0, example=4)
    num_exception_handlers: int = Field(0, ge=0, example=2)
    num_loops: int = Field(0, ge=0, example=3)
    num_conditionals: int = Field(0, ge=0, example=8)
    has_recursion: bool = Field(False, example=False)
    dependencies: List[str] = Field(default_factory=list)
 
 
class BatchPredictRequest(BaseModel):
    project_name: str = Field("unnamed_project", example="cloud-infra-core")
    functions: List[FunctionMetricsRequest]
 
 
class RiskFactorResponse(BaseModel):
    feature: str
    contribution: float
    value: float
    direction: str
 
 
class FunctionRiskResponse(BaseModel):
    function_name: str
    file_path: str
    start_line: int
    end_line: int
    risk_score: float
    risk_level: str
    confidence: float
    priority_rank: int
    top_risk_factors: List[RiskFactorResponse]
    explanation_text: str
    recommended_test_depth: str
    test_types: List[str]
    rf_score: float
    xgb_score: float
 
 
class BatchPredictResponse(BaseModel):
    project: str
    processing_time_ms: float
    summary: Dict[str, Any]
    ranked_functions: List[FunctionRiskResponse]
 
 
# ──────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────
 
def _request_to_metrics(req: FunctionMetricsRequest) -> CodeMetrics:
    return CodeMetrics(
        function_name=req.function_name,
        file_path=req.file_path,
        start_line=req.start_line,
        end_line=req.end_line,
        cyclomatic_complexity=req.cyclomatic_complexity,
        nesting_depth=req.nesting_depth,
        lines_of_code=req.lines_of_code,
        fan_in=req.fan_in,
        fan_out=req.fan_out,
        num_parameters=req.num_parameters,
        commit_frequency=req.commit_frequency,
        author_count=req.author_count,
        bug_history=req.bug_history,
        days_since_last_change=req.days_since_last_change,
        num_return_statements=req.num_return_statements,
        num_exception_handlers=req.num_exception_handlers,
        num_loops=req.num_loops,
        num_conditionals=req.num_conditionals,
        has_recursion=req.has_recursion,
        dependencies=req.dependencies,
    )
 


# Endpoints