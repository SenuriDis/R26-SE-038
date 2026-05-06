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
    """Generates synthetic minority samples by KNN interpolation."""
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
 
