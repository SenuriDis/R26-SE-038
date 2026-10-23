"""
Reproducible evaluation of the C2 risk model, for the research report.

Trains on the same split as train.py (seed 42, stratified 80/20, scaler fitted
on the training part) and writes models/saved/evaluation_report.json with:
  - hold-out metrics for the ensemble and for each member model
  - the cumulative gains curve (share of defects found vs share inspected)
  - size and defect rate of each risk tier
  - stratified 5-fold cross-validation of the whole ensemble
  - global SHAP importance (mean |SHAP| over a sample of test functions)
  - cross-project results: train on four dataset families, test on the fifth

The saved model is left untouched.

Run: python evaluate.py
"""

import os
import sys
import json
import logging

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score, average_precision_score, f1_score, matthews_corrcoef,
    precision_score, recall_score,
)

from data.dataset import load_all_real_datasets
from utils.feature_engineering import FeatureEngineer
from models.risk_detector import MLRiskDetector, RiskThresholds

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("evaluate")

REPORT_PATH = "models/saved/evaluation_report.json"
SEED = 42
SHAP_SAMPLE = 300


def threshold_metrics(y, probs, threshold):
    preds = (probs >= threshold).astype(int)
    return {
        "precision": round(precision_score(y, preds, zero_division=0), 4),
        "recall": round(recall_score(y, preds, zero_division=0), 4),
        "f1": round(f1_score(y, preds, zero_division=0), 4),
        "mcc": round(matthews_corrcoef(y, preds), 4),
    }


def gains_curve(y, probs, step=5):
    """Share of defects found when inspecting functions in descending risk order."""
    found = np.cumsum(y[np.argsort(-probs)]) / y.sum()
    curve = []
    for pct in range(0, 101, step):
        k = int(round(len(y) * pct / 100))
        curve.append({"inspected_pct": pct, "defects_found_pct": round(float(found[k - 1]) * 100, 1) if k else 0.0})
    return curve


def tier_breakdown(y, probs):
    levels = np.array([RiskThresholds.classify(p) for p in probs])
    base = y.mean()
    out = {}
    for tier in ("HIGH", "MEDIUM", "LOW"):
        mask = levels == tier
        rate = float(y[mask].mean()) if mask.any() else None
        out[tier] = {
            "functions": int(mask.sum()),
            "share": round(float(mask.mean()), 4),
            "defect_rate": round(rate, 4) if rate is not None else None,
            "lift": round(rate / base, 2) if rate is not None else None,
            "defects": int(y[mask].sum()),
        }
    return out


def shap_importance(detector, X, n, seed):
    rng = np.random.RandomState(seed)
    rows = X[rng.choice(len(X), size=min(n, len(X)), replace=False)]
    w_rf, w_xgb = detector.W_RF, detector.W_XGB
    phis = np.array([
        (w_rf * detector._rf_explainer.explain(x) + w_xgb * detector._gb_explainer.explain(x)) / (w_rf + w_xgb)
        for x in rows
    ])
    ranked = sorted(zip(detector.feature_names, np.abs(phis).mean(axis=0)), key=lambda t: -t[1])
    return [{"feature": f, "mean_abs_shap": round(float(v), 5)} for f, v in ranked]


def cross_project(X, y, families, seed):
    """Leave-one-family-out: train on four dataset families, test on the fifth.
    Measures how well the model transfers to projects it has never seen."""
    families = np.asarray(families)
    results = {}
    for held_out in sorted(set(families)):
        test = families == held_out
        fe = FeatureEngineer().fit_frame(X[~test])
        detector = MLRiskDetector(random_state=seed).fit(fe.normalise_frame(X[~test]), y[~test])
        probs = detector.predict_proba_batch(fe.normalise_frame(X[test]).values)[0]
        yt = y[test].values
        results[held_out] = {
            "modules": int(test.sum()),
            "defect_rate": round(float(yt.mean()), 4),
            "roc_auc": round(roc_auc_score(yt, probs), 4),
            "pr_auc": round(average_precision_score(yt, probs), 4),
        }
    return results


def evaluate():
    X, y, _, families = load_all_real_datasets("data", with_family=True)
    if X is None:
        sys.exit("No real datasets found under data/ -- nothing to evaluate.")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=SEED
    )
    fe = FeatureEngineer().fit_frame(X_train)
    X_train, X_test = fe.normalise_frame(X_train), fe.normalise_frame(X_test)

    detector = MLRiskDetector(random_state=SEED).fit(X_train, y_train)
    ensemble, rf, xgb = detector.predict_proba_batch(X_test.values)
    lr = detector.lr.predict_proba(detector.scaler.transform(X_test.values.astype(np.float32)))[:, 1]
    yt = y_test.values

    models = {}
    for name, probs in (("ensemble", ensemble), ("random_forest", rf), ("xgboost", xgb), ("logistic_regression", lr)):
        models[name] = {
            "roc_auc": round(roc_auc_score(yt, probs), 4),
            "pr_auc": round(average_precision_score(yt, probs), 4),
            "at_0.5": threshold_metrics(yt, probs, 0.5),
        }

    report = {
        "data": {
            "modules": int(len(X)), "defective": int(y.sum()), "defect_rate": round(float(y.mean()), 4),
            "train": int(len(X_train)), "test": int(len(X_test)), "test_defective": int(yt.sum()),
        },
        "models": models,
        "proposal_targets": {
            "precision_at_high": threshold_metrics(yt, ensemble, RiskThresholds.HIGH)["precision"],
            "recall_at_medium": threshold_metrics(yt, ensemble, RiskThresholds.MEDIUM)["recall"],
            "f1_at_high": threshold_metrics(yt, ensemble, RiskThresholds.HIGH)["f1"],
            "roc_auc": models["ensemble"]["roc_auc"],
        },
        "tiers": tier_breakdown(yt, ensemble),
        "gains_curve": gains_curve(yt, ensemble),
        "cross_validation": {k: round(v, 4) for k, v in detector.cross_validate(X_train, y_train, cv=5).items()},
        "shap_importance": shap_importance(detector, X_test.values.astype(np.float32), SHAP_SAMPLE, SEED),
        "cross_project": cross_project(X, y, families, SEED),
    }

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return report


if __name__ == "__main__":
    r = evaluate()
    e = r["models"]["ensemble"]
    print(f"ROC-AUC {e['roc_auc']}  PR-AUC {e['pr_auc']}  "
          f"CV ROC-AUC {r['cross_validation']['cv_auc_mean']} +/- {r['cross_validation']['cv_auc_std']}")
    print(f"Report written to {REPORT_PATH}")
