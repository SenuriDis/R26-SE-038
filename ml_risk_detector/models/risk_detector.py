import numpy as np
import pandas as pd
import pickle
import os
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
 
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score, classification_report
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
 
logger = logging.getLogger(__name__)
 
 
# ──────────────────────────────────────────────────────────────────────
# SMOTE (pure sklearn/numpy — same algorithm as imbalanced-learn)
# ──────────────────────────────────────────────────────────────────────
 
class SimpleSMOTE:
    """Generates synthetic minority samples"""
    def __init__(self, sampling_strategy: float = 0.4, k_neighbors: int = 5, random_state: int = 42):
        self.sampling_strategy = sampling_strategy
        self.k_neighbors = k_neighbors
        self.rng = np.random.RandomState(random_state)
 
    def fit_resample(self, X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        classes, counts = np.unique(y, return_counts=True)
        majority_class = classes[np.argmax(counts)]
        minority_class = classes[np.argmin(counts)]
        n_majority = counts.max()
        n_minority = counts.min()
        n_target = int(n_majority * self.sampling_strategy)
        n_synthetic = max(0, n_target - n_minority)
 
        if n_synthetic == 0:
            return X, y
 
        X_min = X[y == minority_class]
        nn = NearestNeighbors(n_neighbors=min(self.k_neighbors + 1, len(X_min)))
        nn.fit(X_min)
        _, indices = nn.kneighbors(X_min)
 
        synthetic = []
        for _ in range(n_synthetic):
            idx = self.rng.randint(0, len(X_min))
            nn_idx = indices[idx, self.rng.randint(1, indices.shape[1])]
            gap = self.rng.rand()
            synthetic.append(X_min[idx] + gap * (X_min[nn_idx] - X_min[idx]))
 
        X_synthetic = np.array(synthetic, dtype=X.dtype)
        y_synthetic = np.full(n_synthetic, minority_class, dtype=y.dtype)
        X_out = np.vstack([X, X_synthetic])
        y_out = np.concatenate([y, y_synthetic])
        shuffle = self.rng.permutation(len(X_out))
        return X_out[shuffle], y_out[shuffle]
 
 
# ──────────────────────────────────────────────────────────────────────
# Permutation Explainer (SHAP-compatible schema, model-agnostic)
# ──────────────────────────────────────────────────────────────────────
 
class PermutationExplainer:
    """
    Local feature importance via leave-one-out permutation.
    Approximates SHAP values. Output schema is identical to shap.TreeExplainer
    so the swap is a one-line change when shap becomes available.
    """
    def __init__(self, model, feature_names: List[str]):
        self.model = model
        self.feature_names = feature_names
 
    def explain(self, x: np.ndarray) -> np.ndarray:
        x2d = x.reshape(1, -1)
        base_prob = float(self.model.predict_proba(x2d)[0][1])
        contributions = np.zeros(len(self.feature_names))
        for i in range(len(self.feature_names)):
            x_perturbed = x2d.copy()
            x_perturbed[0, i] = 0.0
            perturbed_prob = float(self.model.predict_proba(x_perturbed)[0][1])
            contributions[i] = base_prob - perturbed_prob
        return contributions
 
 
# ──────────────────────────────────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────────────────────────────────
 
@dataclass
class RiskPrediction:
    function_name: str
    file_path: str
    start_line: int
    end_line: int
    risk_score: float
    risk_level: str
    confidence: float
    priority_rank: int
    top_risk_factors: List[Dict[str, Any]]
    explanation_text: str
    recommended_test_depth: str
    model_rf_score: float
    model_xgb_score: float
 
 
class RiskThresholds:
    HIGH: float = 0.65
    MEDIUM: float = 0.35
 
    @classmethod
    def classify(cls, score: float) -> str:
        if score >= cls.HIGH:
            return "HIGH"
        elif score >= cls.MEDIUM:
            return "MEDIUM"
        return "LOW"
 
    @classmethod
    def test_depth(cls, level: str) -> str:
        return {"HIGH": "exhaustive", "MEDIUM": "boundary", "LOW": "basic"}[level]
 
 
# ──────────────────────────────────────────────────────────────────────
# Main Detector
# ──────────────────────────────────────────────────────────────────────
 
class MLRiskDetector:
    MODEL_VERSION = "1.0.0"
 
    def __init__(self, n_estimators_rf=200, n_estimators_xgb=200, random_state=42, use_smote=True):
        self.random_state = random_state
        self.use_smote = use_smote
        self.scaler = StandardScaler()
        self.feature_names: List[str] = []
        self.is_fitted = False
        self._rf_explainer: Optional[PermutationExplainer] = None
        self._gb_explainer: Optional[PermutationExplainer] = None
 
        self.rf = RandomForestClassifier(
            n_estimators=n_estimators_rf, max_depth=15, min_samples_leaf=3,
            class_weight="balanced", random_state=random_state, n_jobs=-1,
        )
        self.xgb_model = GradientBoostingClassifier(
            n_estimators=n_estimators_xgb, max_depth=5, learning_rate=0.05,
            subsample=0.8, random_state=random_state,
        )
        self.lr = LogisticRegression(
            C=1.0, class_weight="balanced", random_state=random_state, max_iter=1000
        )
        self.smote = SimpleSMOTE(sampling_strategy=0.4, random_state=random_state)
 
    def fit(self, X: pd.DataFrame, y: pd.Series) -> "MLRiskDetector":
        self.feature_names = list(X.columns)
        X_arr = X.values.astype(np.float32)
        logger.info(f"Training: {len(X)} samples, {int(y.sum())} defective ({y.mean()*100:.1f}%)")
 
        if self.use_smote:
            X_arr, y_arr = self.smote.fit_resample(X_arr, y.values)
            logger.info(f"After SMOTE: {len(X_arr)} samples")
        else:
            y_arr = y.values
 
        X_scaled = self.scaler.fit_transform(X_arr)
        logger.info("Fitting Random Forest...")
        self.rf.fit(X_arr, y_arr)
        logger.info("Fitting Gradient Boosting...")
        self.xgb_model.fit(X_arr, y_arr)
        logger.info("Fitting Logistic Regression...")
        self.lr.fit(X_scaled, y_arr)
 
        self._rf_explainer = PermutationExplainer(self.rf, self.feature_names)
        self._gb_explainer = PermutationExplainer(self.xgb_model, self.feature_names)
        self.is_fitted = True
        logger.info("Training complete.")
        return self
 
    def predict_proba_single(self, x: np.ndarray) -> Tuple[float, float, float]:
        x2d = x.reshape(1, -1).astype(np.float32)
        rf_prob = float(self.rf.predict_proba(x2d)[0][1])
        gb_prob = float(self.xgb_model.predict_proba(x2d)[0][1])
        lr_prob = float(self.lr.predict_proba(self.scaler.transform(x2d))[0][1])
        ensemble = 0.40 * rf_prob + 0.50 * gb_prob + 0.10 * lr_prob
        return ensemble, rf_prob, gb_prob
 
    def get_shap_top_factors(self, x: np.ndarray, top_k: int = 3) -> Tuple[List[Dict], str]:
        sv_rf = self._rf_explainer.explain(x.astype(np.float32))
        sv_gb = self._gb_explainer.explain(x.astype(np.float32))
        sv = 0.5 * sv_rf + 0.5 * sv_gb
        sorted_idx = np.argsort(np.abs(sv))[::-1][:top_k]
        factors = []
        for idx in sorted_idx:
            factors.append({
                "feature": self.feature_names[idx],
                "contribution": float(sv[idx]),
                "value": float(x[idx]),
                "direction": "increases" if sv[idx] > 0 else "decreases",
            })
        parts = [
            f"{f['feature'].replace('_', ' ').title()} "
            f"({'high' if f['contribution'] > 0 else 'low'}: {f['value']:.1f})"
            for f in factors
        ]
        return factors, "Risk driven by: " + ", ".join(parts)
 
    def get_confidence(self, score: float, rf_score: float, xgb_score: float) -> float:
        agreement = 1.0 - abs(rf_score - xgb_score)
        decisiveness = abs(score - 0.5) * 2
        return float(min(0.5 * agreement + 0.5 * decisiveness + 0.1, 1.0))
 
    def predict_batch(self, feature_matrix: np.ndarray, metadata: List[Dict]) -> List[RiskPrediction]:
        if not self.is_fitted:
            raise RuntimeError("Model not fitted.")
        results = []
        for i, x in enumerate(feature_matrix):
            ensemble_score, rf_score, xgb_score = self.predict_proba_single(x)
            confidence = self.get_confidence(ensemble_score, rf_score, xgb_score)
            top_factors, explanation = self.get_shap_top_factors(x, top_k=3)
            risk_level = RiskThresholds.classify(ensemble_score)
            meta = metadata[i] if i < len(metadata) else {}
            results.append(RiskPrediction(
                function_name=meta.get("function_name", f"func_{i}"),
                file_path=meta.get("file_path", "unknown"),
                start_line=meta.get("start_line", 0),
                end_line=meta.get("end_line", 0),
                risk_score=ensemble_score,
                risk_level=risk_level,
                confidence=confidence,
                priority_rank=0,
                top_risk_factors=top_factors,
                explanation_text=explanation,
                recommended_test_depth=RiskThresholds.test_depth(risk_level),
                model_rf_score=rf_score,
                model_xgb_score=xgb_score,
            ))
        results.sort(key=lambda r: r.risk_score, reverse=True)
        for rank, result in enumerate(results, start=1):
            result.priority_rank = rank
        return results
 
    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        X_arr = X.values.astype(np.float32)
        probs = np.array([self.predict_proba_single(x)[0] for x in X_arr])
        preds = (probs >= RiskThresholds.HIGH).astype(int)
        preds_recall = (probs >= RiskThresholds.MEDIUM).astype(int)
        metrics = {
            "precision": precision_score(y, preds, zero_division=0),
            "recall": recall_score(y, preds_recall, zero_division=0),
            "f1_score": f1_score(y, preds, zero_division=0),
            "roc_auc": roc_auc_score(y, probs),
        }
        for k, v in metrics.items():
            logger.info(f"  {k}: {v:.4f}")
        logger.info(classification_report(y, preds, target_names=["Clean", "Defective"]))
        return metrics
 
    def cross_validate(self, X: pd.DataFrame, y: pd.Series, cv: int = 5) -> Dict[str, float]:
        X_arr = X.values.astype(np.float32)
        skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=self.random_state)
        f1_scores = cross_val_score(self.rf, X_arr, y.values, cv=skf, scoring="f1", n_jobs=-1)
        auc_scores = cross_val_score(self.rf, X_arr, y.values, cv=skf, scoring="roc_auc", n_jobs=-1)
        result = {
            "cv_f1_mean": float(f1_scores.mean()), "cv_f1_std": float(f1_scores.std()),
            "cv_auc_mean": float(auc_scores.mean()), "cv_auc_std": float(auc_scores.std()),
        }
        logger.info(f"CV F1: {result['cv_f1_mean']:.3f}±{result['cv_f1_std']:.3f}  "
                    f"AUC: {result['cv_auc_mean']:.3f}±{result['cv_auc_std']:.3f}")
        return result
 
    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({
                "rf": self.rf, "xgb_model": self.xgb_model, "lr": self.lr,
                "scaler": self.scaler, "feature_names": self.feature_names,
                "is_fitted": self.is_fitted, "version": self.MODEL_VERSION,
            }, f)
        logger.info(f"Model saved → {path}")
 
    @classmethod
    def load(cls, path: str) -> "MLRiskDetector":
        with open(path, "rb") as f:
            state = pickle.load(f)
        d = cls()
        d.rf = state["rf"]; d.xgb_model = state["xgb_model"]; d.lr = state["lr"]
        d.scaler = state["scaler"]; d.feature_names = state["feature_names"]
        d.is_fitted = state["is_fitted"]
        d._rf_explainer = PermutationExplainer(d.rf, d.feature_names)
        d._gb_explainer = PermutationExplainer(d.xgb_model, d.feature_names)
        logger.info(f"Model loaded ← {path}")
        return d
 
