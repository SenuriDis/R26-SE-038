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

### 2. C2 — inference uses an unfitted FeatureEngineer  *(affects all scores)*

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

`pipeline/runners/c2_predict.py` works around this by loading the fitted
pickle, and warns loudly if it is missing.

**Both are in Vihanga's component and are left unmodified here on purpose** —
editing vendored subtree code creates conflicts on the next `git subtree pull`.
They should be fixed on `origin/Vihanga` and pulled in.

### 3. Async functions are invisible to C1

C1's `FeatureExtractor`, `FunctionComplexityCalculator` and
`FunctionInfoAdapter` all match `ast.FunctionDef` only, never
`ast.AsyncFunctionDef`. Any `async def` is dropped from analysis entirely.
Stage 1 counts and reports these rather than hiding them, but the real fix
belongs in C1.

### 4. Stage 2 cannot run in this environment yet  *(current blocker)*

C2 needs `numpy`, `pandas`, `scikit-learn`, `xgboost`. The repo venv is C3's
(chromadb / llama-index) and has none of them. C2's pinned `numpy==1.26.4` has
**no wheels for Python 3.13**, which is the only interpreter installed here.

Options, in order of preference:

1. Create a C2 venv on Python 3.11 or 3.12 and install
   `components/c2_ml_risk/requirements.txt` as pinned, then point at it with
   `C2_PYTHON`. Keeps the pickled model loading against the sklearn version it
   was trained on.
2. Relax the pins to `numpy>=2.1`, `scikit-learn>=1.5` on 3.13. The
   `risk_detector.pkl` was pickled under sklearn 1.4.2, so it may warn or fail
   to unpickle — retraining via `train.py` would then be required.

## Status

- [x] Branch created, C1 + C2 vendored with history
- [x] Stage 1: C1 runs, both artifacts written
- [x] C1 -> C2 adapter: all 20 fields, verified against source
- [ ] Stage 2: blocked on C2 environment (issue 4)
- [ ] Backfill the 4 git-history fields and `fan_in`
- [ ] Stage 3: vendor C3 and wire `ml_report_reader.py` to artifact 03
- [ ] Stage 4: vendor C4 (Nisula) for test execution
