# Integration Pipeline — Notes

Branch: `integration/pipeline`

This branch wires the separately-developed components into one flow. No
component branch is modified; C1 and C2 were brought in with `git subtree`, so
their full history is preserved and later updates can be pulled with
`git subtree pull`.

## Layout

```
components/
  c1_static_analysis/   <- git subtree of origin/Senuri
  c2_ml_risk/           <- git subtree of origin/Vihanga
pipeline/
  contracts.py          <- artifact names + the C1->C2 field mapping
  extractors/           <- the 8 AST metrics C1 measures but never writes out
  stages/               <- orchestrator side of each stage
  runners/              <- scripts that execute inside a component's own env
run_pipeline.py         <- CLI entry point
artifacts/              <- stage output (gitignored)
```

## The flow

```
target (.py file or directory)
   |
   v  stage 1  -- C1, components/c1_static_analysis
   |
   +--> artifacts/01_static_analysis.json    C1's native per-file output
   +--> artifacts/02_c2_input.json           flattened to C2's BatchPredictRequest
   |
   v  stage 2  -- C2, components/c2_ml_risk
   |
   +--> artifacts/03_ml_output.json          tier_breakdown payload
   |
   v  stage 3  -- C3  [NOT WIRED YET]
        src/utils/ml_report_reader.py already reads exactly this format
```

Stages talk only through JSON files, so any stage can be re-run on its own
against the previous stage's output:

```bash
python run_pipeline.py <target>              # whole pipeline
python run_pipeline.py <target> --only 1     # just C1 + the adapter
python run_pipeline.py <target> --only 2     # just C2, on existing artifacts
```

### Why each stage is a subprocess

Two reasons, both structural rather than stylistic:

- **Dependency conflicts.** C2 pins `numpy==1.26.4` / `scikit-learn==1.4.2`.
  C3's environment is built around chromadb and needs a much newer numpy.
  They cannot share an interpreter.
- **Module name collisions.** C1 imports itself as `src.*`, C3 also has a
  `src/`, and C2 uses bare `utils.*` and `models.*`. In one process these
  shadow each other depending on import order.

Interpreters are selected with `--c1-python` / `--c2-python`, or the
`C1_PYTHON` / `C2_PYTHON` environment variables.

## C1 -> C2 field mapping

C2's `FunctionMetricsRequest` has 20 fields. Where each comes from:

**7 forwarded from C1** — `function_name`, `file_path`,
`cyclomatic_complexity`, `nesting_depth`, `lines_of_code`, `dependencies`,
`fan_out`.

C1's `FunctionInfoAdapter` already computes per-function `nesting_depth` and
`lines_of_code`, and keeps the live `ast.FunctionDef` node on every
`FunctionInfo` — which is what makes the next group free.

**8 derived from that AST node** (`pipeline/extractors/function_metrics.py`) —
`start_line`, `end_line`, `num_parameters`, `num_return_statements`,
`num_exception_handlers`, `num_loops`, `num_conditionals`, `has_recursion`.

Counts stop at nested function boundaries: a loop inside a closure belongs to
the closure. C1 emits a separate `FunctionInfo` for each nested function, so
counting the nested body in both places would double-count it.

**5 still at defaults** — `commit_frequency`, `author_count`, `bug_history`,
`days_since_last_change`, `fan_in`.

> These are not cosmetic. `bug_history` is the **single largest SHAP
> contributor** in C2's own sample output, so risk scores stay compressed until
> the four git-history fields are filled. Backfilling means mining git per
> function (blame the function's line range, then aggregate the commits that
> touched it). `fan_in` needs a cross-file call graph.

## Open issues found while integrating

### 1. C2 — `/health` is not registered  *(blocker for HTTP mode)*

`components/c2_ml_risk/ml_risk_detector/api/predict_api.py:154`

```python
app.get("/health")      # missing the @ — this is a call, not a decorator
async def health():
```

The decorator `@` is missing, so the route is never registered and
`GET /health` returns 404. Every other route in the file has it.

### 2a. C2 — the committed model file is stale  *(this is the big one)*

`models/saved/risk_detector.pkl` does not match any committed FeatureEngineer.

Evidence — commit dates on `origin/Vihanga`:

| file | committed | commit |
|---|---|---|
| `feature_engineer.pkl` | 2026-05-07 | `aebd066` |
| `sample_prediction.json` | 2026-05-07 | `aebd066` |
| `risk_detector.pkl` | 2026-05-10 | `7e89c5f` |
| `risk_detector_fe.pkl` | 2026-05-10 | `7e89c5f` |

Scoring the `process_transaction` example from `predict_api.py` against the
recorded result of **0.4294**:

| model + FeatureEngineer | score |
|---|---|
| committed model + `feature_engineer.pkl` | 0.0411 |
| committed model + `risk_detector_fe.pkl` | 0.0411 |
| committed model + unfitted FE (API path) | 0.9999 |
| **freshly trained via `train.py`** | **0.429** ✅ |

Re-running `train.py` unmodified reproduces the documented sample exactly —
score 0.429, MEDIUM, and the same three SHAP factors (bug_history, num_loops,
dependency_count). So the training code is correct and the committed `.pkl`
is simply out of date with its FeatureEngineer.

`data/dataset.py` generates synthetic data with `random_state=42`, so training
is deterministic and reproducible. **Fix: re-run `train.py` and commit both
pickles together.**

### 2b. C2 — inference uses an unfitted FeatureEngineer  *(affects all scores)*

`train.py` fits the FeatureEngineer for z-score normalisation and pickles it:

```python
fe = FeatureEngineer(); fe.fit(m_train)          # train.py:47-48
pickle.dump(fe, open("models/saved/feature_engineer.pkl", "wb"))   # train.py:95
```

but `predict_api.py` startup builds a bare one and never loads that file:

```python
_feature_engineer = FeatureEngineer()            # never fitted
```

`FeatureEngineer.transform` silently returns **raw, unnormalised** features
when `_fit_stats is None`. So the API feeds unnormalised features to a model
trained on z-scored ones. This likely explains the compressed scores in
`sample_prediction.json` (average risk 0.1438, zero HIGH-risk functions).

`pipeline/runners/c2_predict.py` loads the fitted pickle instead, and warns
loudly if it is missing. Note this alone does **not** fix the scores while
issue 2a stands — with the stale model both fitted pickles give 0.0411.

**Both are in Vihanga's component and are left unmodified here on purpose** —
editing vendored subtree code creates conflicts on the next `git subtree pull`.
They should be fixed on `origin/Vihanga` and pulled in.

### 3. Async functions are invisible to C1

C1's `FeatureExtractor`, `FunctionComplexityCalculator` and
`FunctionInfoAdapter` all match `ast.FunctionDef` only, never
`ast.AsyncFunctionDef`. Any `async def` is dropped from analysis entirely.
Stage 1 counts and reports these rather than hiding them, but the real fix
belongs in C1.

### 4. C2's requirements.txt overstates what it needs  *(resolved)*

`requirements.txt` pins xgboost, shap, imbalanced-learn, jupyter, matplotlib
and seaborn. **None of them are imported anywhere in the package** — the
`xgb_model` attribute is really an sklearn `GradientBoostingClassifier`, and
`SimpleSMOTE` / `PermutationExplainer` are hand-rolled in `risk_detector.py`.

The prediction path needs only `numpy`, `pandas`, `scikit-learn`.

Environment now in place: `components/c2_ml_risk/venv` on **Python 3.12.10**
with numpy 1.26.4, pandas 2.2.1, scikit-learn 1.4.2 — C2's exact pins.
`stage2_ml_risk.resolve_python()` finds it automatically.

(C2's pinned `numpy==1.26.4` has no Python 3.13 wheels, which is why 3.12 was
needed. The repo's own venv is C3's and stays untouched.)

### 5. Real code scores flat, because 5 features are constants

With the pipeline running end to end over 91 real functions from C1's `src/`:

| model | distinct scores | range | tiers |
|---|---|---|---|
| committed | 2 | 0.000 – 0.042 | 91 LOW |
| freshly trained | 4 | 0.000 – 0.046 | 91 LOW |

Retraining does **not** fix this, because the cause is upstream: every function
carries `bug_history=0`, `commit_frequency=0`, `author_count=1`,
`days_since_last_change=999`, `fan_in=0`. Those five feed six of the model's
engineered features, including `change_risk` and `total_coupling`.

RandomForest importances on the current model:

```
structural_complexity      0.1061
change_risk                0.1010   <- placeholder-driven
dependency_count           0.0961
fan_out                    0.0957
num_conditionals           0.0950
bug_history                0.0950   <- placeholder-driven
complexity_nesting_product 0.0905
commit_frequency           0.0804   <- placeholder-driven
```

The model was trained on synthetic data where risky functions have heavy git
churn. Real functions reporting zero churn all look safe, and ranking then
falls to noise — `parse` (cc=2) outscores `_parse_block` (cc=9).

A sensitivity sweep confirms the lever: holding code metrics fixed and moving
only the git fields to realistic values moved the score 0.042 -> 0.147.

**So backfilling the git fields is required, not an optimisation.**

## Status

- [x] Branch created, C1 + C2 vendored with history
- [x] Stage 1: C1 runs, both artifacts written
- [x] C1 -> C2 adapter: all 20 fields, verified against source
- [x] C2 environment: Python 3.12 venv with C2's exact pins
- [x] **Stage 2 runs end to end — C1 -> C2 -> 03_ml_output.json**
- [ ] Backfill the 4 git-history fields and `fan_in` (issue 5 — next up)
- [ ] Get C2's model artifacts regenerated and committed (issue 2a — Vihanga)
- [ ] Stage 3: vendor C3 and wire `ml_report_reader.py` to artifact 03
- [ ] Stage 4: vendor C4 (Nisula) for test execution

The connection between C1 and C2 is proven working. The *scores* it currently
carries are not yet meaningful, for the reasons in issues 2a and 5.
