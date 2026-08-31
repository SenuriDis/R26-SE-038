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
from utils.llm_prompt_generator import LLMPromptGenerator
 
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
    generate_llm_prompt: bool = Field(False, description="If true, generates a structured text prompt for an LLM to generate test cases.")
 
 
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
    llm_prompt: Optional[str] = None
 
 
# Convert JSON to CodeMetrics object from component 1
 
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

app.get("/health")
async def health():
    return {
        "status": "healthy",
        "model_loaded": _detector is not None and _detector.is_fitted,
        "version": "1.0.0",
    }
 
 
@app.get("/model/info")
async def model_info():
    if _detector is None or not _detector.is_fitted:
        raise HTTPException(status_code=503, detail="Model not loaded.")
    return {
        "model_version": MLRiskDetector.MODEL_VERSION,
        "features": _detector.feature_names,
        "thresholds": {
            "HIGH": 0.65,
            "MEDIUM": 0.35,
        },
        "ensemble": "RandomForest(40%) + XGBoost(50%) + LogisticRegression(10%)",
    }
 
 # Prediction endpoint - Functions metrics gannwa, and risk scores and prioritization gannwa.
@app.post("/predict", response_model=BatchPredictResponse)
async def predict(request: BatchPredictRequest):
    """
    Main prediction endpoint. Accepts a batch of functions with code metrics.
    Returns risk scores, SHAP explanations, and test prioritization.
 
    This is the primary interface between Component 2 and Component 3.
    """
    if _detector is None or not _detector.is_fitted:
        raise HTTPException(status_code=503, detail="Model not loaded. POST /train first.")
 
    t0 = time.time()
 
    # Build CodeMetrics objects
    metrics_list = [_request_to_metrics(fn) for fn in request.functions]
 
    # Extract features needed
    fe = _feature_engineer or FeatureEngineer()
    feature_matrix = np.stack([
        fe.transform(m) for m in metrics_list
    ])
 
    # Metadata for predictions
    metadata = [
        {
            "function_name": m.function_name,
            "file_path": m.file_path,
            "start_line": m.start_line,
            "end_line": m.end_line,
        }
        for m in metrics_list
    ]
 
    # Predict
    predictions: List[RiskPrediction] = _detector.predict_batch(feature_matrix, metadata)
 
    # Prioritize
    payload = _prioritizer.prioritize(predictions, project_name=request.project_name)
 
    elapsed_ms = (time.time() - t0) * 1000
 
    # Build response
    TEST_TYPE_MAP = {
        "exhaustive": ["boundary_tests", "negative_tests", "edge_cases", "exception_handling"],
        "boundary": ["boundary_tests", "typical_inputs"],
        "basic": ["happy_path"],
    }
 
    ranked = []
    for fn in payload["ranked_functions"]:
        ranked.append(FunctionRiskResponse(
            function_name=fn["function_name"],
            file_path=fn["file_path"],
            start_line=fn["start_line"],
            end_line=fn["end_line"],
            risk_score=fn["risk_score"],
            risk_level=fn["risk_level"],
            confidence=fn["confidence"],
            priority_rank=fn["priority_rank"],
            top_risk_factors=[RiskFactorResponse(**rf) for rf in fn["top_risk_factors"]],
            explanation_text=fn["explanation_text"],
            recommended_test_depth=fn["recommended_test_depth"],
            test_types=fn["test_types"],
            rf_score=fn["rf_score"],
            xgb_score=fn["xgb_score"],
        ))
 
    llm_prompt_text = None
    if getattr(request, "generate_llm_prompt", False):
        llm_prompt_text = LLMPromptGenerator.generate_prompt(payload)

    return BatchPredictResponse(
        project=request.project_name,
        processing_time_ms=round(elapsed_ms, 2),
        summary=payload["summary"],
        ranked_functions=ranked,
        llm_prompt=llm_prompt_text,
    )
 
 
@app.post("/train")
async def train_model():
    """
    Train (or retrain) the model on synthetic data.
    In production, replace with real dataset loading from repository mining.
    """
    global _detector, _feature_engineer
 
    logger.info("Starting model training...")
 
        # For demonstration, created synthetic dataset with 2000 samples.
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from data.dataset import generate_synthetic_dataset
    from sklearn.model_selection import train_test_split
 
    X, y, metrics_list = generate_synthetic_dataset(n_samples=2000, random_state=42) # gen synthetic data
 
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
 
    fe = FeatureEngineer()
    fe.fit(metrics_list[:len(X_train)]) # compute normalization params on train set
 
    detector = MLRiskDetector()
    detector.fit(X_train, y_train)
    metrics = detector.evaluate(X_test, y_test)
 
    # Save
    os.makedirs("models/saved", exist_ok=True)
    detector.save(MODEL_PATH)
    fe_path = MODEL_PATH.replace(".pkl", "_fe.pkl")
    import pickle
    with open(fe_path, "wb") as f:
        pickle.dump(fe, f)
 
    _detector = detector
    _feature_engineer = fe
 
    return {
        "status": "trained",
        "evaluation": {k: round(v, 4) for k, v in metrics.items()},
        "model_path": MODEL_PATH,
    }
 
