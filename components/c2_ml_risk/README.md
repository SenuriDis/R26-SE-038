# Component 2 — ML-Based High-Risk Code Detection
# IT22292872 - W.M.V.S.B Wahundeniya
**IT4010 Research Project 2026 · R26-SE-038**

---

## Overview
This component receives function-level code metrics from Component 1 (Static Code Analysis),
applies machine learning models to predict defect risk, and outputs prioritised risk scores
with SHAP-based explanations to Component 3 (LLM Test Generation).

## Pipeline

```
02_c2_input.json  (20 metric fields per function, from C1 + AST + git history)
      │
      ▼
FeatureEngineer      16 raw + 6 derived features, z-score normalised
      │
      ▼
MLRiskDetector       RandomForest 0.40 + XGBoost 0.50 + LogisticRegression 0.10 (soft vote)
      │              shap.TreeExplainer → top-3 risk factors per function
      ▼
TestPrioritizer      HIGH ≥ 0.65 → exhaustive · MEDIUM ≥ 0.35 → boundary · LOW → happy path
      │
      ▼
03_ml_output.json    ranked functions + tier breakdown, read by C3
```

## Model

| Part | Details |
| --- | --- |
| Training data | 20,030 unique modules (22.3% defective) from NASA MDP / PROMISE, PSOWE, the 2022 TSE CPDP benchmark (NASA, SOFTLAB) and SoftwareDefectDataset, mapped onto one 22-feature schema |
| Imbalance | SMOTE on the training split only (k = 5, minority grown to 40% of the majority) |
| Ensemble | Random Forest (200 trees, depth 15) · XGBoost (200 estimators, depth 5, lr 0.05) · Logistic Regression |
| Explanations | Exact TreeSHAP in probability units, blended with the ensemble weights; reported with real metric values, e.g. `Lines Of Code = 87 (raises risk)` |
| Confidence | Agreement between the two tree models plus distance from 0.5 |

## Usage

All commands run from `ml_risk_detector/`.

```bash
pip install -r ../requirements.txt

python train.py        # train on data/, save models/saved/*.pkl and a sample prediction
python evaluate.py     # write models/saved/evaluation_report.json (does not touch the model)
pytest tests/ -v       # unit, dataset and API tests

uvicorn api.predict_api:app --host 0.0.0.0 --port 8002
```

| Endpoint | Purpose |
| --- | --- |
| `POST /predict` | Score, explain and rank a batch of functions |
| `POST /train` | Retrain on the real datasets (synthetic fallback) |
| `GET /model/info` | Model version, features, thresholds, ensemble weights |
| `GET /health` | Liveness and whether a model is loaded |

`MODEL_PATH` (default `models/saved/risk_detector.pkl`) selects the model; the fitted
scaler is read from the same path with a `_fe` suffix.

## Results

From `models/saved/evaluation_report.json` (seed 42, stratified 80/20 split):

| Metric | Value |
| --- | --- |
| ROC-AUC (hold-out) | 0.686 |
| PR-AUC (hold-out, base rate 0.223) | 0.397 |
| ROC-AUC, 5-fold CV of the full ensemble | 0.684 ± 0.005 |
| Defects in the riskiest 30% of functions | 50.1% |
| Defect rate in the HIGH tier | 56.1% (2.5× base rate) |
| Cross-project ROC-AUC (train on 4 families, test on the 5th) | 0.494 – 0.727 |

The public datasets carry no version-control history, so the four git process metrics are
constant in training and do not yet influence predictions.
