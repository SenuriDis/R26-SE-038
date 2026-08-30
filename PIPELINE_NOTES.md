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
  c3_llm_tests/         <- git subtree of origin/Harrish-model-change
  c4_test_eval/         <- git subtree of origin/Nisula
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
   +--> artifacts/04_spec_contract.json      documented contract, for C3
   |
   v  stage 2  -- C2, components/c2_ml_risk
   |
   +--> artifacts/03_ml_output.json          tier_breakdown payload
   |
   v  stage 3  -- C3, components/c3_llm_tests
   |
   +--> artifacts/c3_output/run_<id>/  generated tests, review, traceability
   |
   v  stage 4  -- C4, components/c4_test_eval
   |
   +--> artifacts/c4_workdir/reports/evaluation_report.json
```

Artifact 04 leaves the chain at stage 1 and goes straight to C3:

```
C1 ──code metrics──▶ C2 ──risk report──▶ C3
 └──documented contract (artifact 04)───▶ ┘
```

C2's `FunctionMetricsRequest` has no field for documentation — no coverage,
no gaps, no declared exceptions — so routing C1's requirement analysis
through C2 would silently discard it. Artifact 04 keys each record on
`function_name` + `file_path` so it joins onto the ML report inside C3.

C1's own `FeatureMatrixBuilder` drops the `Requirement` object, keeping only
counts and booleans derived from it. Stage 1 therefore calls
`CodeRequirementMapper` directly to retain the contract itself, because
`"raises ValueError when amount < 0"` is a test case while
`"exception_requirements_count: 1"` is not.

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

### 5b. Backfill done — and validated on a real repository

`pipeline/extractors/git_history.py` now mines all four fields per function
via `git log -L <start>,<end>:<file>`, which follows a line range backwards
through history as it moves.

Running it against C1's own `src/` produced no change in scores. That turned
out to be a property of the target, not a bug: C1 is a solo-author project
with 1–3 commits per function and **zero** bug-fix commits, while the model
was trained on synthetic data resembling PROMISE/NASA defect sets.

Re-running against **psf/requests** (6,493 commits, 790 authors) tells a very
different story:

| field | C1's src/ | requests |
|---|---|---|
| `commit_frequency` | 1–3 (3 distinct) | 1–92 (39 distinct) |
| `author_count` | always 1 | 1–38 (24 distinct) |
| `bug_history` | **always 0** | 0–29 (17 distinct) |
| distinct risk scores | 2 | **33** |
| tiers | 91 LOW | 1 MEDIUM, 265 LOW |

The ranking it produces is plausible on its face — top functions are
`resolve_redirects` (sessions.py), `send` (adapters.py), `request`
(sessions.py), `prepare_body` (models.py): genuinely the most-patched parts
of that library.

Both the committed and a freshly-trained model produce the **same ordering**,
differing only in absolute score (0.358 vs 0.289 at the top). So the
prioritisation is trustworthy even while issue 2a is unresolved.

Two things remain open:

- **Nothing reaches HIGH.** The top real-world function scores 0.358 against
  a HIGH threshold of 0.65. Either the thresholds are calibrated for a score
  distribution the model doesn't actually produce, or the synthetic training
  data is more extreme than real code. Worth raising with Vihanga.
- **Speed — and a correction.** An earlier version of this file blamed the
  runtime on git mining. That was wrong; the stages were never timed apart.
  Measured separately on requests (266 functions):

  | stage | time |
  |---|---|
  | stage 1, no git | **1.0 s** |
  | stage 1, with git mining | **22.6 s** |
  | stage 2 (C2 scoring) | **3 m 22 s** |

  Git mining costs ~80 ms per function, not the ~0.7 s previously claimed.
  The bottleneck is **C2**, specifically `PermutationExplainer.explain()`,
  which loops over all 22 features per function and re-predicts each time
  across a 200-tree forest and a 200-estimator booster. That is roughly
  760 ms per function and it dominates everything else combined.

  Worth raising with Vihanga: the explanation step could be limited to the
  top-ranked functions rather than every one, since only high-risk functions
  need SHAP factors injected into C3's prompts.

## Status

- [x] Branch created, C1 + C2 vendored with history
- [x] Stage 1: C1 runs, both artifacts written
- [x] C1 -> C2 adapter: all 20 fields, verified against source
- [x] C2 environment: Python 3.12 venv with C2's exact pins
- [x] **Stage 2 runs end to end — C1 -> C2 -> 03_ml_output.json**
- [x] Backfill the 4 git-history fields (issue 5b)
- [x] Validated end to end on psf/requests — 266 functions, sensible ranking
- [ ] `fan_in` — still the one unsourced field; needs a call graph
- [ ] Get C2's model artifacts regenerated and committed (issue 2a — Vihanga)
- [ ] Tier thresholds vs real-world score range (issue 5b — Vihanga)
- [x] Stage 3: C3 vendored and wired — runs end to end
- [x] Stage 4: C4 vendored and wired — runs end to end

C1 -> C2 is connected, validated, and produces a defensible risk ranking on
real code. 19 of the 20 fields carry real measurements; only `fan_in` is
still a placeholder.

### 6. C1 only reads Google-style docstrings  *(limits artifact 04)*

`DocstringRequirementExtractor` states it plainly: *"Only Google-style
Args/Returns/Raises sections are recognised."* Sphinx/reST docstrings
(`:param x:`, `:raises ValueError:`) are invisible to it.

That style is extremely common in the third-party repos this path was built
for. Demonstrated with two functions that mean exactly the same thing:

| function | style | result |
|---|---|---|
| `charge_google` | Google | inputs, returns, exceptions `[ValueError, LookupError]` |
| `charge_rest` | reST | `implemented_undocumented` — nothing extracted |

On psf/requests the effect is total: 226 functions, **zero** declared
exceptions found. The 155 input constraints that did come through are from
the type-hint fallback, not docstrings.

Since declared exceptions are the most directly useful thing here — each one
is a negative test case — teaching the extractor reST would roughly double
what artifact 04 is worth on real repositories. That belongs in C1.

The reproduction case is `scratchpad/styletest/billing.py`.

**What does work well:** gap detection. Given a docstring promising
`ValueError` where the body never raises, C1 correctly reports
`missing_input_validation` and `missing_exception_handling`. That is a real
defect found from documentation alone, and exactly the kind of test worth
generating.

### 7. Stage 3 notes

C3 already ships a full CLI, so stage 3 wraps it rather than reimplementing.
It runs on the repo venv, which was built for C3's dependencies.

**It is off by default.** Every selected function costs several Groq calls
across three agents, throttled to ~24/min, so a plain run stops after stage 2
and prints what stage 3 *would* process. `--stage3` actually runs it, and
`--min-risk-level` controls how far down the tiers it goes.

**Credentials.** C3 resolves `.env` relative to its cwd, which is its own
vendored directory. Rather than copy secrets in there — where they could be
committed by accident — the repo-root `.env` is parsed and passed through the
subprocess environment. Environment variables outrank the file in
pydantic-settings, so C3 needs no change.

**Ollama is not needed.** `settings.py` configures `ollama_model_agent2:
deepseek-coder:33b`, but `agent2_test_validation.py` calls
`build_groq_llm(settings.groq_model_agent1, ...)`. All three agents are on
Groq; the Ollama settings are vestigial. Worth deleting or wiring up, since
right now they suggest a dependency that doesn't exist.

**Windows console crash (worked around).** C3's `print_summary` emits emoji.
Windows defaults to cp1252, which cannot encode them, so it raises
`UnicodeEncodeError` — *after* every output file has been written. The run
looks failed when it actually succeeded. Stage 3 sets `PYTHONIOENCODING=utf-8`
on the child to avoid it, but the real fix belongs in C3.

### 8. C3 output — earlier conclusion was wrong

**An earlier version of this file said C3's output "varies a lot between
identical runs" and implied a reliability problem. That was wrong, and the
fault was in this pipeline.** Two separate causes, both now understood.

**Cause 1 — absolute file paths (a bug in stage 1, fixed).**

C3 treats `file_path` as repo-relative. `CodeExtractor` joins it
(`repo_path / file_path`) and, more importantly, `RepositoryRetriever` embeds
it *verbatim into the RAG query text*:

```python
query = f"...for the function '{function_name}' in '{file_path}'"
```

Stage 1 was emitting absolute Windows paths, so every retrieval query carried
160 characters of `C:\Users\...\AppData\Local\Temp\claude\<uuid>\scratchpad\`
noise. That is a semantic embedding query, and the indexer labels its own
chunks with *relative* paths — so the query vector was dominated by
irrelevant path tokens and retrieval returned poor context.

Stage 1 now resolves the target's git root and emits `src/requests/utils.py`,
matching the format C3's own demos use. The root is recorded in artifact 02
as `repo_root`, and stage 3 passes it as `--repo-path` so both sides agree.

**Cause 2 — the sample was the single hardest function in the library.**

C2 ranked exactly one function MEDIUM: `resolve_redirects`. Every stage 3 run
therefore targeted it, and it is a worst case — ~150 lines, a generator,
requiring a full `Session.send` loop to be mocked. Agent 3's own review calls
it out for handling "redirect logic, cookie merging, auth rebuilding, proxy
handling, and body rewinding".

Measured on three ordinary functions instead (complexity 4–5, ~22 lines):

| target | valid tests | traceability |
|---|---|---|
| `unquote_unreserved` | ✅ | **8/8** |
| `generate` | ✅ (2 repairs) | **8/8** |
| `__call__` | ✅ | **6/6** |
| **overall** | **3/3 (100%)** | **perfect** |

versus `resolve_redirects`: 0/1 valid, 0/7 traced.

So C3 performs as its author reported. The honest limitation is narrower:
very large multi-responsibility functions defeat it. Worth noting in the
research write-up as a real boundary, not a defect.

#### Historical: the runs that prompted the wrong conclusion

Three runs on the same function, same config, no code changes between them:

| run | tests generated | valid | traceability | repairs |
|---|---|---|---|---|
| `9636767f` | 6, named `test_tc001…tc006` | 1/1 ✅ | **6/7 (86%)** | 1 |
| `374a2712` | 1, named `test_resolve_redirects_simple` | 1/1 ✅ | **0/7** | 3 |
| `163494b5` | 5 | **0/1 ❌** | **0/7** | — |

All three targeted `resolve_redirects` with absolute paths in the RAG query,
so the spread reflects an LLM struggling on a worst-case function with poor
retrieval context — not general instability. With both causes fixed, ordinary
functions come out at 100% with perfect traceability.

One observation still worth keeping: the traceability matcher looks for a test
function per `TC00n` id, so it scores well only when Agent 1 follows the
`test_tc001_*` naming convention. Run `374a2712` named its single test
`test_resolve_redirects_simple` and scored 0/7. On the three ordinary
functions the convention held and traceability was perfect, so this only
surfaces when generation is already going badly — but a matcher that also
compared descriptions would be more robust.

**It does find real bugs.** On `requests.resolve_redirects`, Agent 3 reported
HIGH: *"when yield_requests=True the generator yields the prepared request but
never updates the URL or breaks the loop, causing an infinite loop."*

### 9. Stage 4 notes

C4 is built around its own sample project: `execute_tests.py` derives
`SRC_DIR`, `TESTS_DIR` and `REPORTS_DIR` from `BASE_DIR` — the directory the
script itself sits in — and its Dockerfile copies its own `src/` and `tests/`.

Rather than change any of that, stage 4 stages a directory in exactly the
shape C4 expects and drops an unmodified copy of its script in:

```
<artifacts>/c4_workdir/
    execute_tests.py    copied from C4, unmodified
    src/                the target's importable source root
    tests/              C3's generated tests
    reports/            C4's output
```

Because `BASE_DIR` follows the script, everything resolves inside the workdir
and C4 evaluates the target instead of its own samples. The staged `src/` is
put first on `PYTHONPATH` so it wins over any installed copy of the same
package — otherwise coverage measures site-packages.

**Result on requests** (2 generated test files, 16 tests):

| metric | value |
|---|---|
| pass rate | 15/16 (93.75%) |
| statement coverage | 23.96% |
| branch coverage | 5.47% |
| failure classification | 1 "Invalid AI Test" (a `TypeError`) |

The classification is correct — that test really was malformed rather than
finding a defect.

**Coverage denominator is the whole package, not the functions under test.**
C4 runs `--cov={SRC_DIR}`, so those percentages are "coverage of all 2,368
statements in requests by tests for 2 functions". That is why the grade comes
out "D — Needs Improvement". For evaluating targeted AI-generated tests, the
meaningful denominator is the functions C3 was asked to cover. Worth raising
with Nisula — as it stands, the grade will always look poor on a real repo no
matter how good the tests are.

**Mutation testing does not work here.** Two independent reasons:

- mutmut 3.x refuses to run on Windows at all ("please use the WSL").
- mutmut 2.4.4 does run, but mutates *all* of `src/`. On requests that is
  thousands of mutants each requiring a full suite run; a 15-minute cap was
  not close to enough. It is only practical on C4's own small samples.

Scoping mutation to the functions under test would fix the second and is the
same change as the coverage-denominator one. The first needs Docker or WSL.

### 9b. C4 — the failure classifier misfires  *(this one matters)*

`classify_failure` tests its patterns in the wrong order:

```python
if "assertionerror" in error_message or "assert " in error_message:
    return "Real Defect"
elif "syntaxerror" in ... or "typeerror" in ... or "attributeerror" in ...:
    return "Invalid AI Test"
```

It is fed `t["call"]["longrepr"]` — pytest's full traceback, which includes
the failing **source line**. Because most test failures happen on an `assert`
statement, the literal substring `assert ` is present in almost every
traceback, so the first branch catches nearly everything before the error-type
checks are ever reached.

Verified with a purpose-built probe (`scratchpad/c4probe/`), three failures
engineered to land in three different categories:

| test | actual error | expected | C4 said |
|---|---|---|---|
| `test_real_defect` | `AssertionError` | Real Defect | Real Defect ✅ |
| `test_invalid_ai_test` | **`AttributeError`** | Invalid AI Test | **Real Defect ❌** |
| `test_environment_failure` | `ModuleNotFoundError` | Environment Failure | Environment Failure ✅ |

The middle traceback contains both `assert ` and `attributeerror`; the
ordering makes `assert ` win.

Consequence: C4 systematically **over-reports "Real Defect" and under-reports
"Invalid AI Test"** — which inverts the component's headline claim of telling
genuine defects apart from bad AI tests. On the requests run one `TypeError`
*was* classified correctly, but only because that failure happened during the
call rather than on an assert line.

Fix is small: check the concrete exception type first and fall back to
`assert` only when no known type matches. Better still, use the structured
`call.crash` / `longrepr.reprcrash.message` field from pytest's JSON report,
which gives the exception type alone without the surrounding source.

**Cosmetic issues in C4's report output:** the repository name is hardcoded
(`print("calculator-app")  # Hardcoded`), and it prints `Environment: Docker`
/ `Docker Environment: DESTROYED` unconditionally — including on this local
run, where no container was involved. The JSON also carries mojibake
(`"quality_grade": "D � Needs Improvement"`) because it is written without an
explicit encoding.

**Docker was not used.** C4's intended path is `run.py`, which builds an image
and runs the suite inside it. Docker is installed here but the daemon is not
running, and C4's Dockerfile copies its own `src/`/`tests/` rather than a
target, so it would need parameterising for arbitrary repos anyway. Stage 4
runs locally instead — no isolation, but no daemon required.

## Reproducing the validation run

```bash
git clone https://github.com/psf/requests.git /tmp/requests
python run_pipeline.py /tmp/requests/src/requests --project-name requests
```

Expect ~3 minutes, 266 functions, `resolve_redirects` ranked first.
