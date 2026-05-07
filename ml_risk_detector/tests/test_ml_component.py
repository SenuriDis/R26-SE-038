"""
tests/test_ml_component.py
Unit + integration tests for Component 2.
Run: pytest tests/ -v
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pandas as pd
import pytest
import json

from utils.feature_engineering import FeatureEngineer, CodeMetrics
from models.risk_detector import MLRiskDetector, RiskThresholds, RiskPrediction
from models.prioritizer import TestPrioritizer
from data.dataset import generate_synthetic_dataset


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def sample_metrics():
    return CodeMetrics(
        function_name="process_transaction",
        file_path="src/payment.py",
        start_line=45,
        end_line=78,
        cyclomatic_complexity=18,
        nesting_depth=5,
        lines_of_code=87,
        fan_in=3,
        fan_out=12,
        num_parameters=4,
        commit_frequency=23,
        author_count=4,
        bug_history=3,
        days_since_last_change=7,
        num_return_statements=5,
        num_exception_handlers=3,
        num_loops=4,
        num_conditionals=12,
        has_recursion=False,
        dependencies=["dep_a", "dep_b", "dep_c"],
    )


@pytest.fixture(scope="module")
def low_risk_metrics():
    return CodeMetrics(
        function_name="format_receipt",
        file_path="src/output.py",
        start_line=1, end_line=20,
        cyclomatic_complexity=2,
        nesting_depth=1,
        lines_of_code=18,
        fan_in=5, fan_out=1,
        num_parameters=2,
        commit_frequency=2,
        author_count=1,
        bug_history=0,
        days_since_last_change=120,
        num_return_statements=1,
        num_exception_handlers=0,
        num_loops=0, num_conditionals=1,
        has_recursion=False,
        dependencies=["dep_x"],
    )


@pytest.fixture(scope="module")
def trained_detector():
    """Train a small model for testing."""
    X, y, metrics_list = generate_synthetic_dataset(n_samples=500, random_state=42)
    detector = MLRiskDetector(n_estimators_rf=50, n_estimators_xgb=50, random_state=42)
    detector.fit(X, y)
    return detector


@pytest.fixture(scope="module")
def feature_engineer(trained_detector):
    X, y, metrics_list = generate_synthetic_dataset(n_samples=500, random_state=42)
    fe = FeatureEngineer()
    fe.fit(metrics_list)
    return fe


# ──────────────────────────────────────────────────────────────────────
# Feature Engineering Tests
# ──────────────────────────────────────────────────────────────────────

class TestFeatureEngineering:

    def test_extract_features_keys(self, sample_metrics):
        fe = FeatureEngineer()
        features = fe.extract_features(sample_metrics)
        assert set(features.keys()) == set(FeatureEngineer.FEATURE_NAMES)

    def test_derived_complexity_density(self, sample_metrics):
        fe = FeatureEngineer()
        features = fe.extract_features(sample_metrics)
        expected = sample_metrics.cyclomatic_complexity / sample_metrics.lines_of_code
        assert abs(features["complexity_density"] - expected) < 1e-6

    def test_transform_returns_correct_length(self, sample_metrics):
        fe = FeatureEngineer()
        vec = fe.transform(sample_metrics)
        assert len(vec) == len(FeatureEngineer.FEATURE_NAMES)

    def test_batch_transform_shape(self, sample_metrics, low_risk_metrics):
        fe = FeatureEngineer()
        matrix = fe.transform_batch([sample_metrics, low_risk_metrics])
        assert matrix.shape == (2, len(FeatureEngineer.FEATURE_NAMES))

    def test_from_json_roundtrip(self, sample_metrics):
        data = {
            "function_name": sample_metrics.function_name,
            "file_path": sample_metrics.file_path,
            "start_line": sample_metrics.start_line,
            "end_line": sample_metrics.end_line,
            "cyclomatic_complexity": sample_metrics.cyclomatic_complexity,
            "nesting_depth": sample_metrics.nesting_depth,
            "lines_of_code": sample_metrics.lines_of_code,
            "fan_in": sample_metrics.fan_in,
            "fan_out": sample_metrics.fan_out,
            "num_parameters": sample_metrics.num_parameters,
            "commit_frequency": sample_metrics.commit_frequency,
            "bug_history": sample_metrics.bug_history,
            "dependencies": sample_metrics.dependencies,
        }
        parsed = FeatureEngineer.from_json(data)
        assert parsed.function_name == sample_metrics.function_name
        assert parsed.cyclomatic_complexity == sample_metrics.cyclomatic_complexity

    def test_fit_sets_stats(self):
        X, y, metrics_list = generate_synthetic_dataset(n_samples=100)
        fe = FeatureEngineer()
        fe.fit(metrics_list)
        assert fe._fit_stats is not None
        assert "cyclomatic_complexity" in fe._fit_stats


# ──────────────────────────────────────────────────────────────────────
# Risk Thresholds Tests
# ──────────────────────────────────────────────────────────────────────

class TestRiskThresholds:

    def test_high_classification(self):
        assert RiskThresholds.classify(0.80) == "HIGH"
        assert RiskThresholds.classify(0.65) == "HIGH"

    def test_medium_classification(self):
        assert RiskThresholds.classify(0.50) == "MEDIUM"
        assert RiskThresholds.classify(0.35) == "MEDIUM"

    def test_low_classification(self):
        assert RiskThresholds.classify(0.20) == "LOW"
        assert RiskThresholds.classify(0.00) == "LOW"

    def test_test_depth_mapping(self):
        assert RiskThresholds.test_depth("HIGH") == "exhaustive"
        assert RiskThresholds.test_depth("MEDIUM") == "boundary"
        assert RiskThresholds.test_depth("LOW") == "basic"


# ──────────────────────────────────────────────────────────────────────
# ML Model Tests
# ──────────────────────────────────────────────────────────────────────

class TestMLRiskDetector:

    def test_model_is_fitted(self, trained_detector):
        assert trained_detector.is_fitted

    def test_feature_names_populated(self, trained_detector):
        assert len(trained_detector.feature_names) == len(FeatureEngineer.FEATURE_NAMES)

    def test_predict_proba_range(self, trained_detector):
        X, y, _ = generate_synthetic_dataset(n_samples=20, random_state=99)
        x = X.values[0].astype(np.float32)
        score, rf_score, xgb_score = trained_detector.predict_proba_single(x)
        assert 0.0 <= score <= 1.0
        assert 0.0 <= rf_score <= 1.0
        assert 0.0 <= xgb_score <= 1.0

    def test_high_risk_function_scores_high(self, trained_detector, feature_engineer, sample_metrics):
        x = feature_engineer.transform(sample_metrics)
        score, _, _ = trained_detector.predict_proba_single(x)
        # High CC=18, nesting=5, commits=23, bugs=3 → should score higher than 0.5
        assert score > 0.4, f"Expected high-risk function to score >0.4, got {score:.3f}"

    def test_low_risk_function_scores_low(self, trained_detector, feature_engineer, low_risk_metrics):
        x = feature_engineer.transform(low_risk_metrics)
        score, _, _ = trained_detector.predict_proba_single(x)
        assert score < 0.7, f"Expected low-risk function to score <0.7, got {score:.3f}"

    def test_shap_returns_top_3(self, trained_detector, feature_engineer, sample_metrics):
        x = feature_engineer.transform(sample_metrics)
        factors, explanation = trained_detector.get_shap_top_factors(x, top_k=3)
        assert len(factors) == 3
        for factor in factors:
            assert "feature" in factor
            assert "contribution" in factor
            assert "value" in factor
            assert "direction" in factor

    def test_shap_explanation_text(self, trained_detector, feature_engineer, sample_metrics):
        x = feature_engineer.transform(sample_metrics)
        _, explanation = trained_detector.get_shap_top_factors(x)
        assert isinstance(explanation, str)
        assert len(explanation) > 10

    def test_batch_predict_length(self, trained_detector, feature_engineer, sample_metrics, low_risk_metrics):
        metrics_list = [sample_metrics, low_risk_metrics]
        feature_matrix = feature_engineer.transform_batch(metrics_list)
        metadata = [
            {"function_name": m.function_name, "file_path": m.file_path,
             "start_line": m.start_line, "end_line": m.end_line}
            for m in metrics_list
        ]
        predictions = trained_detector.predict_batch(feature_matrix, metadata)
        assert len(predictions) == 2

    def test_batch_predict_ranked(self, trained_detector, feature_engineer, sample_metrics, low_risk_metrics):
        feature_matrix = feature_engineer.transform_batch([sample_metrics, low_risk_metrics])
        metadata = [
            {"function_name": m.function_name, "file_path": m.file_path,
             "start_line": m.start_line, "end_line": m.end_line}
            for m in [sample_metrics, low_risk_metrics]
        ]
        predictions = trained_detector.predict_batch(feature_matrix, metadata)
        # Should be sorted descending by risk score
        assert predictions[0].risk_score >= predictions[1].risk_score

    def test_batch_predict_rank_assigned(self, trained_detector, feature_engineer, sample_metrics, low_risk_metrics):
        feature_matrix = feature_engineer.transform_batch([sample_metrics, low_risk_metrics])
        metadata = [
            {"function_name": m.function_name, "file_path": m.file_path,
             "start_line": m.start_line, "end_line": m.end_line}
            for m in [sample_metrics, low_risk_metrics]
        ]
        predictions = trained_detector.predict_batch(feature_matrix, metadata)
        assert predictions[0].priority_rank == 1
        assert predictions[1].priority_rank == 2

    def test_model_save_load(self, trained_detector, tmp_path):
        path = str(tmp_path / "test_model.pkl")
        trained_detector.save(path)
        loaded = MLRiskDetector.load(path)
        assert loaded.is_fitted
        assert loaded.feature_names == trained_detector.feature_names

    def test_evaluate_returns_metrics(self, trained_detector):
        X, y, _ = generate_synthetic_dataset(n_samples=100, random_state=77)
        metrics = trained_detector.evaluate(X, y)
        required = {"precision", "recall", "f1_score", "roc_auc"}
        assert required.issubset(set(metrics.keys()))

    def test_confidence_between_0_and_1(self, trained_detector):
        for score, rf, xgb in [(0.8, 0.75, 0.85), (0.3, 0.25, 0.35), (0.5, 0.5, 0.5)]:
            c = trained_detector.get_confidence(score, rf, xgb)
            assert 0.0 <= c <= 1.0


# ──────────────────────────────────────────────────────────────────────
# Test Prioritizer Tests
# ──────────────────────────────────────────────────────────────────────

class TestPrioritizer:

    def test_prioritize_returns_all_tiers(self, trained_detector, feature_engineer):
        X, y, metrics_list = generate_synthetic_dataset(n_samples=20, random_state=42)
        feature_matrix = feature_engineer.transform_batch(metrics_list[:20])
        metadata = [
            {"function_name": m.function_name, "file_path": m.file_path,
             "start_line": m.start_line, "end_line": m.end_line}
            for m in metrics_list[:20]
        ]
        predictions = trained_detector.predict_batch(feature_matrix, metadata)
        prioritizer = TestPrioritizer()
        payload = prioritizer.prioritize(predictions, project_name="test_project")

        assert "summary" in payload
        assert "tier_breakdown" in payload
        assert "ranked_functions" in payload
        assert "HIGH" in payload["tier_breakdown"]
        assert "MEDIUM" in payload["tier_breakdown"]
        assert "LOW" in payload["tier_breakdown"]

    def test_summary_counts_match(self, trained_detector, feature_engineer):
        X, y, metrics_list = generate_synthetic_dataset(n_samples=20, random_state=42)
        feature_matrix = feature_engineer.transform_batch(metrics_list[:20])
        metadata = [
            {"function_name": m.function_name, "file_path": m.file_path,
             "start_line": m.start_line, "end_line": m.end_line}
            for m in metrics_list[:20]
        ]
        predictions = trained_detector.predict_batch(feature_matrix, metadata)
        prioritizer = TestPrioritizer()
        payload = prioritizer.prioritize(predictions)

        s = payload["summary"]
        total = s["high_risk_count"] + s["medium_risk_count"] + s["low_risk_count"]
        assert total == s["total_functions"]

    def test_json_export(self, trained_detector, feature_engineer, tmp_path):
        X, y, metrics_list = generate_synthetic_dataset(n_samples=10, random_state=42)
        feature_matrix = feature_engineer.transform_batch(metrics_list[:10])
        metadata = [
            {"function_name": m.function_name, "file_path": m.file_path,
             "start_line": m.start_line, "end_line": m.end_line}
            for m in metrics_list[:10]
        ]
        predictions = trained_detector.predict_batch(feature_matrix, metadata)
        prioritizer = TestPrioritizer()
        payload = prioritizer.prioritize(predictions)

        out = str(tmp_path / "output.json")
        prioritizer.export_json(payload, out)
        assert os.path.exists(out)
        with open(out) as f:
            loaded = json.load(f)
        assert "ranked_functions" in loaded


# ──────────────────────────────────────────────────────────────────────
# Dataset Tests
# ──────────────────────────────────────────────────────────────────────

class TestDataset:

    def test_generates_correct_size(self):
        X, y, metrics = generate_synthetic_dataset(n_samples=200)
        assert len(X) == 200
        assert len(y) == 200
        assert len(metrics) == 200

    def test_defect_ratio_approximately_correct(self):
        X, y, _ = generate_synthetic_dataset(n_samples=2000, defect_ratio=0.15)
        actual_ratio = y.mean()
        assert 0.10 <= actual_ratio <= 0.20

    def test_feature_columns_present(self):
        X, y, _ = generate_synthetic_dataset(n_samples=100)
        from data.dataset import FEATURE_COLUMNS
        assert set(FEATURE_COLUMNS).issubset(set(X.columns))

    def test_no_nan_values(self):
        X, y, _ = generate_synthetic_dataset(n_samples=200)
        assert not X.isnull().any().any()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])