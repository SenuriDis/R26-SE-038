import os
import sys
import json
import logging
 
sys.path.insert(0, os.path.dirname(__file__))
 
# pyrefly: ignore [missing-import]
import numpy as np
from sklearn.model_selection import train_test_split
 
from data.dataset import generate_synthetic_dataset
from utils.feature_engineering import FeatureEngineer, CodeMetrics
from models.risk_detector import MLRiskDetector
from models.prioritizer import TestPrioritizer
from utils.llm_prompt_generator import LLMPromptGenerator
 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("train")
 
# Function to run  the ML risk detector training pipeline 
def train():
    print("\n" + "="*65)
    print("   ML RISK DETECTOR TRAINING PIPELINE")
    print("  W.M.V.S.B Wahundeniya - IT22292872")
    print("="*65 + "\n")
 
    # ── 1. Generate / load dataset ──────────────────────────────────
    logger.info("Step 1: Generating synthetic training dataset...")
    X, y, metrics_list = generate_synthetic_dataset(
        n_samples=3000,
        defect_ratio=0.15,
        random_state=42,
    )
 
    # Train / test split (80/20 stratified)
    X_train, X_test, y_train, y_test, m_train, m_test = train_test_split(
        X, y, metrics_list, test_size=0.20, stratify=y, random_state=42
    )
    logger.info(f"Train: {len(X_train)} | Test: {len(X_test)}")
 
    # ── 2. Feature engineering ──────────────────────────────────────
    logger.info("Step 2: Fitting FeatureEngineer (z-score normalisation)...")
    fe = FeatureEngineer()
    fe.fit(m_train)
 
    # ── 3. Train model ──────────────────────────────────────────────
    logger.info("Step 3: Training RF + XGBoost ensemble with SMOTE...")
    detector = MLRiskDetector(
        n_estimators_rf=200,
        n_estimators_xgb=200,
        use_smote=True,
        random_state=42,
    )
    detector.fit(X_train, y_train)
 
    # ── 4. Evaluate ─────────────────────────────────────────────────
    logger.info("Step 4: Evaluating on hold-out test set...")
    metrics = detector.evaluate(X_test, y_test)
 
    print("\n" + "-"*55)
    print("  HOLD-OUT TEST SET RESULTS")
    print("-"*55)
    targets = {
        "precision":       ("Precision >=0.85", 0.85),
        "recall":          ("Recall >=0.80",     0.80),
        "f1_score":        ("F1-score >=0.82",   0.82),
        "roc_auc":         ("ROC-AUC >=0.80",    0.80),
    }
    all_pass = True
    for key, (label, threshold) in targets.items():
        val = metrics.get(key, 0)
        status = "[PASS]" if val >= threshold else "[MISS]"
        if val < threshold:
            all_pass = False
        print(f"  {label:<22} : {val:.4f}   {status}")
    print("-"*55)
    print(f"  Proposal targets: {'ALL MET [PASS]' if all_pass else 'Some targets need tuning'}")
 
    # ── 5. Cross-validation ─────────────────────────────────────────
    logger.info("Step 5: 5-fold cross-validation...")
    cv_metrics = detector.cross_validate(X_train, y_train, cv=5)
    print(f"\n  CV F1:  {cv_metrics['cv_f1_mean']:.3f} +/- {cv_metrics['cv_f1_std']:.3f}")
    print(f"  CV AUC: {cv_metrics['cv_auc_mean']:.3f} +/- {cv_metrics['cv_auc_std']:.3f}")
 
    # ── 6. Save model ───────────────────────────────────────────────
    logger.info("Step 6: Saving model...")
    os.makedirs("models/saved", exist_ok=True)
    detector.save("models/saved/risk_detector.pkl")
 
    import pickle
    with open("models/saved/feature_engineer.pkl", "wb") as f:
        pickle.dump(fe, f)
 
    # ── 7. Demo prediction ──────────────────────────────────────────
    logger.info("Step 7: Running demo prediction on known high-risk function...")
 
    # This mirrors the process_transaction() function from the UI mockup in the proposal
    process_transaction = CodeMetrics(
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
        dependencies=["validate_input", "calculate_tax", "update_ledger", "send_notification",
                      "log_event", "check_limits", "apply_currency_conversion",
                      "notify_fraud_service", "record_audit", "emit_event",
                      "refresh_cache", "send_webhook"],
    )
 
    validate_payment = CodeMetrics(
        function_name="validate_payment",
        file_path="src/payment.py",
        start_line=112,
        end_line=140,
        cyclomatic_complexity=9,
        nesting_depth=3,
        lines_of_code=45,
        fan_in=8,
        fan_out=5,
        num_parameters=3,
        commit_frequency=12,
        author_count=2,
        bug_history=1,
        days_since_last_change=14,
        num_return_statements=4,
        num_exception_handlers=1,
        num_loops=1,
        num_conditionals=6,
        has_recursion=False,
        dependencies=["check_card", "verify_cvv", "validate_amount", "check_expiry", "lookup_bank"],
    )
 
    format_receipt = CodeMetrics(
        function_name="format_receipt",
        file_path="src/output.py",
        start_line=34,
        end_line=52,
        cyclomatic_complexity=2,
        nesting_depth=1,
        lines_of_code=18,
        fan_in=5,
        fan_out=1,
        num_parameters=2,
        commit_frequency=3,
        author_count=1,
        bug_history=0,
        days_since_last_change=90,
        num_return_statements=1,
        num_exception_handlers=0,
        num_loops=0,
        num_conditionals=1,
        has_recursion=False,
        dependencies=["format_date"],
    )
 
    test_functions = [process_transaction, validate_payment, format_receipt]
 
    # Build feature matrix
    feature_vectors = np.stack([fe.transform(m) for m in test_functions])
    metadata = [
        {"function_name": m.function_name, "file_path": m.file_path,
         "start_line": m.start_line, "end_line": m.end_line}
        for m in test_functions
    ]
 
    predictions = detector.predict_batch(feature_vectors, metadata)
 
    prioritizer = TestPrioritizer()
    payload = prioritizer.prioritize(predictions, project_name="payment-service-demo")
    prioritizer.print_summary(payload)
 
    # the output for the top function
    print("\n  DETAILED SHAP EXPLANATION - process_transaction():")
    print("  " + "-"*55)
    top = next(p for p in predictions if p.function_name == "process_transaction")
    print(f"  Risk score  : {top.risk_score:.3f}  [{top.risk_level}]")
    print(f"  Confidence  : {top.confidence:.3f}")
    print(f"  RF model    : {top.model_rf_score:.3f}")
    print(f"  XGB model   : {top.model_xgb_score:.3f}")
    print(f"  Test depth  : {top.recommended_test_depth}")
    print(f"  Explanation : {top.explanation_text}")
    print("\n  Top SHAP factors:")
    for factor in top.top_risk_factors:
        bar = "=" * int(abs(factor["contribution"]) * 80)
        print(f"    {factor['feature']:<35} +{factor['contribution']:+.3f}  {bar}")
 
    # JSON file save
    out_path = "models/saved/sample_prediction.json"
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    logger.info(f"Sample prediction saved to {out_path}")
    
    prompt_out_path = "models/saved/sample_llm_prompt.txt"
    LLMPromptGenerator.export_prompt(payload, prompt_out_path)
    logger.info(f"Sample LLM Prompt saved to {prompt_out_path}")
 
    print("\n  Training complete. Model ready for API deployment.")
    print("  Run: uvicorn api.predict_api:app --host 0.0.0.0 --port 8000\n")
 
    return detector, fe, metrics
 
 
if __name__ == "__main__":
    train()
 

