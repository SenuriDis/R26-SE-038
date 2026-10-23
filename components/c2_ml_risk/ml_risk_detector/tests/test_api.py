"""
tests/test_api.py
Endpoint tests for the C2 FastAPI service, run against the saved model.
Run: pytest tests/ -v
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient

from api.predict_api import app, MODEL_PATH
from models.risk_detector import MLRiskDetector, RiskThresholds

pytestmark = pytest.mark.skipif(not os.path.exists(MODEL_PATH), reason="no saved model to serve")


@pytest.fixture(scope="module")
def client():
    # The context manager runs the startup hook, which loads the model
    with TestClient(app) as c:
        yield c


RISKY = {
    "function_name": "process_transaction", "file_path": "src/payment.py",
    "start_line": 45, "end_line": 131,
    "cyclomatic_complexity": 18, "nesting_depth": 5, "lines_of_code": 87,
    "fan_in": 3, "fan_out": 12, "num_parameters": 4,
    "commit_frequency": 23, "author_count": 4, "bug_history": 3, "days_since_last_change": 7,
    "num_return_statements": 5, "num_exception_handlers": 3, "num_loops": 4,
    "num_conditionals": 12, "has_recursion": False,
    "dependencies": [f"dep_{i}" for i in range(12)],
}
SIMPLE = {
    "function_name": "format_receipt", "file_path": "src/output.py",
    "start_line": 34, "end_line": 52,
    "cyclomatic_complexity": 2, "nesting_depth": 1, "lines_of_code": 18,
    "fan_in": 5, "fan_out": 1, "num_parameters": 2,
    "num_return_statements": 1, "num_conditionals": 1, "dependencies": ["format_date"],
}


def test_health_reports_loaded_model(client):
    body = client.get("/health").json()
    assert body["status"] == "healthy"
    assert body["model_loaded"] is True
    assert body["version"] == MLRiskDetector.MODEL_VERSION


def test_model_info_matches_detector(client):
    body = client.get("/model/info").json()
    assert body["thresholds"] == {"HIGH": RiskThresholds.HIGH, "MEDIUM": RiskThresholds.MEDIUM}
    assert len(body["features"]) == 22
    assert body["explainer"] == "shap.TreeExplainer"


def test_predict_ranks_and_explains(client):
    r = client.post("/predict", json={"project_name": "api-test", "functions": [SIMPLE, RISKY]})
    assert r.status_code == 200
    ranked = r.json()["ranked_functions"]
    assert [f["priority_rank"] for f in ranked] == [1, 2]
    assert ranked[0]["risk_score"] >= ranked[1]["risk_score"]
    for f in ranked:
        assert len(f["top_risk_factors"]) == 3
        assert f["explanation_text"].startswith("Risk driven by:")
        assert f["risk_level"] in ("HIGH", "MEDIUM", "LOW")


def test_predict_rejects_impossible_metrics(client):
    bad = dict(SIMPLE, cyclomatic_complexity=0)   # CC is at least 1
    r = client.post("/predict", json={"functions": [bad]})
    assert r.status_code == 422
