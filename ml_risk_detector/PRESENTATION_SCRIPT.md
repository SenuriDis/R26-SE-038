# Component 2: ML Risk Detection — 2-Minute Presentation Script

---

## **OPENING [15 seconds]**

"Component 2 is the ML brain of our system. Its job is simple: take code metrics from Component 1 and predict which functions are most likely to have bugs. Then rank them so Component 3 knows which ones need the most rigorous testing.

Think of it as a risk scorer — it turns static code analysis into actionable, ranked predictions."

---

## **THE PIPELINE [30 seconds]**

"Here's how it works:

First, we receive function metrics — cyclomatic complexity, nesting depth, lines of code, fan-in and fan-out coupling, commit frequency, author count, bug history, and dependency count.

These raw metrics go through **feature engineering**. We normalize them using z-score normalization so the ML model can work with them properly. We also derive new features — for example, complexity density, which is complexity divided by lines of code. This helps the model spot patterns better.

Then the normalized features go into our **ensemble ML model**."

---

## **THE ML MODEL [35 seconds]**

"We use three models working together:

1. **Random Forest** — builds many decision trees and averages them. It's great at finding non-linear patterns in code complexity and coupling.

2. **Gradient Boosting** — also uses trees, but builds them sequentially. Each tree corrects the errors of the previous one, which often gives us better accuracy on tricky cases.

3. **Logistic Regression** — a simple linear model. We include it as a stable baseline that keeps the ensemble grounded.

The final risk score is a weighted average: 40% Random Forest, 50% Gradient Boosting, 10% Logistic Regression.

To handle imbalanced data — where buggy functions are rare — we use **SMOTE**, which creates synthetic examples of defect-prone code near real ones. This balances the training set."

---

## **EXPLAINABILITY [25 seconds]**

"We implemented a permutation explainer — similar to SHAP values — that tells us which features most influenced each risk prediction.

For example, if a function gets a high risk score, the explainer says: 'This is high risk because cyclomatic complexity is 18, fan-out is 9, and it has previous bug history.'

This transparency is crucial for Component 3 — the LLM uses these top risk factors in its test generation prompts."

---

## **THE OUTPUT [20 seconds]**

"The model produces three outputs per function:

1. **Risk Score** — a probability from 0 to 1
2. **Risk Level** — HIGH (≥0.65), MEDIUM (0.35–0.65), or LOW (<0.35)
3. **Test Depth** — exhaustive, boundary, or basic

Then **TestPrioritizer** ranks all functions and creates a JSON payload:
- TOP 20% get exhaustive testing — boundary cases, edge cases, exceptions
- NEXT 30% get boundary testing — parameter limits and typical inputs
- BOTTOM 50% get basic happy-path tests

This payload is passed directly to Component 3."

---

## **DATA AND TRAINING [15 seconds]**

"Right now, we're using synthetic training data — it's realistic but generated for demo purposes. The synthetic defective functions have higher complexity, more dependencies, more commits, and more bug history.

In production, we'd replace this with real bug history mined from repositories using GitPython. We'd extract actual defects from issue trackers and link them to code metrics.

That's the vision for the next phase — real data makes the model actually predictive of real bugs."

---

## **CLOSING [10 seconds]**

"So to summarize: Component 2 is a risk-ranking engine. It transforms code metrics into interpretable risk predictions, explains why each function is risky, and hands off a prioritized list to Component 3 for test generation.

Questions?"

---

## **TIMING BREAKDOWN**
- Opening: 15s
- Pipeline: 30s
- ML Model: 35s
- Explainability: 25s
- Output: 20s
- Data & Training: 15s
- Closing: 10s
- **Total: ~150 seconds (2.5 minutes with natural pauses)**

---

## **PRESENTATION TIPS**

### Visuals to show (if you have slides):
1. Data flow diagram: Component 1 → Feature Engineering → ML Ensemble → Risk Scores → Prioritizer → Component 3
2. Feature examples: cyclomatic complexity, fan-out, bug history
3. Ensemble weights: RF 40%, GB 50%, LR 10%
4. Risk threshold visualization: 0.35–0.65 (MEDIUM), ≥0.65 (HIGH)
5. Sample output: ranked functions with risk scores and top factors

### Key phrases to emphasize:
- "Risk **scorer** — turns static analysis into predictions"
- "**Ensemble** of three models — more robust than any single model"
- "**SMOTE** balances rare defects"
- "**Permutation explainer** provides transparency"
- "**20% exhaustive, 30% boundary, 50% basic** testing allocation"

### Common questions & quick answers:
- **Q: Why three models?** A: Different models capture different patterns. Ensemble reduces mistakes.
- **Q: How is the model trained?** A: Synthetic data now, real bug history in production.
- **Q: Why is SHAP important?** A: Component 3 needs to know WHY functions are risky for better test generation.
- **Q: How do you know if the model works?** A: Precision, recall, F1-score, and ROC-AUC on a holdout test set.

---

## **FINAL PROJECT SCOPE & INTEGRATION**

"The final system is an end-to-end intelligent testing platform. Component 1 performs static analysis and extracts function-level metrics. Component 2 uses those metrics to predict risk and prioritize functions. Component 3 generates, validates, and reviews pytest test cases for the highest-risk functions using RAG-augmented LLMs.

In the final architecture, the flow is:
1. Repository mining and AST parsing in Component 1
2. Feature engineering and ML risk scoring in Component 2
3. Structured test generation and code review in Component 3
4. Output storage and reporting for stakeholders

The system integrates through JSON payloads and API contracts. Component 1 supplies metrics either directly to Component 2 or through an API. Component 2 exposes a `/predict` endpoint that returns ranked risk results and test guidance. Component 3 consumes that ranked payload, uses the file path and function context for RAG, and generates validated tests and review reports.

The ultimate goal is a seamless pipeline where risk analysis directs expensive LLM effort only to the code that needs it most, while preserving transparency and traceability across all components."

---

**Good luck with your presentation!**
