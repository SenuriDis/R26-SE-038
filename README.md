# R26-SE-038 — LLM and ML Enhanced Software Testing System

**IT4010 Research Project — 2026**

An automated testing system built from four components. This branch
(`integration/pipeline`) wires all four into a single end-to-end flow.

| # | Component | Author | What it does |
|---|---|---|---|
| 1 | Static Code Analysis | Senuri Dissanayake (IT22210692) | Parses the repo, measures complexity, compares code against its documentation |
| 2 | ML Risk Detection | W.M.V.S.B Wahundeniya (IT22292872) | Scores each function's defect risk and ranks what to test |
| 3 | LLM Test Generation | Harrish Shermon (IT22177964) | Generates pytest tests and reviews code, using three LLM agents |
| 4 | Test Execution | Premaratne R.A.N.C (IT22050908) | Runs the generated tests, measures coverage, classifies failures |

Each component also lives on its own branch. Here they are brought together
with `git subtree`, so their history is preserved and updates can be pulled
back in later.

---

## What happens when you run it

```
  your repository
        │
        ▼
  ┌───────────────┐   measures every function, mines git history,
  │ 1  Analysis   │   reads docstrings and compares them to the code
  └───────┬───────┘
          │  01_static_analysis.json   02_c2_input.json   04_spec_contract.json
          ▼
  ┌───────────────┐   predicts which functions are most likely to
  │ 2  ML Risk    │   contain defects, and ranks them HIGH/MEDIUM/LOW
  └───────┬───────┘
          │  03_ml_output.json
          ▼
  ┌───────────────┐   writes pytest tests for the risky functions
  │ 3  Test Gen   │   and reviews the code, using three LLM agents
  └───────┬───────┘
          │  generated_tests/  code_review_report.json  traceability_report.json
          ▼
  ┌───────────────┐   runs those tests, measures coverage, and says
  │ 4  Execution  │   whether each failure is a real bug or a bad test
  └───────┬───────┘
          │  evaluation_report.json
          ▼
      the result
```

Every stage reads and writes JSON files, so any stage can be re-run on its own
against the previous stage's output.

---

## Setup

You need **Python 3.12** installed ([download][py312]). Components 2 and 4
require it — component 2 pins numpy 1.26.4, which has no Python 3.13 build.

```bash
git clone <repo-url>
cd Intelligent-software-testing-system
git checkout integration/pipeline

python setup_pipeline.py
```

That builds three virtual environments. They are separate because the
components need conflicting versions of the same libraries and cannot share
one interpreter.

Finally, create a `.env` file in the repo root with your Groq key — component
3's agents need it:

```
GROQ_API_KEY=your_key_here
```

[py312]: https://www.python.org/downloads/release/python-31210/

---

## Demo — the quickest way to show it working

There is a small example project at `examples/demo_project/` with two
deliberate problems planted in it:

- `apply_discount` has a real bug — it forgets to divide the percentage by 100
- `charge` has a docstring promising a `ValueError` that the code never raises

Run the whole pipeline against it:

```bash
python run_pipeline.py examples/demo_project --min-risk-level LOW --stage3 --stage4
```

Takes two to four minutes, nearly all of it component 3 waiting on the Groq
rate limit. Here is what to point at as it runs.

**Stage 1** finds the documentation gap without running anything:

```
documented funcs : 3 / 3
```

`artifacts/04_spec_contract.json` shows `charge` flagged with
`missing_exception_handling` — the promised `ValueError` is nowhere in the code.

**Stage 3** writes tests and reviews the code. Its review independently finds
the same gap:

```
[HIGH] The function promises to raise a ValueError when `amount` exceeds
       `balance` but never performs this check, allowing negative balances.
```

**Stage 4** runs the generated tests and catches the planted bug:

```
Passed : 8      Line Coverage   : 77.78%
Failed : 2      Branch Coverage : 70.0%

Real Defect         : 2
Invalid AI Test     : 0
Environment Failure : 0
```

with the actual assertion visible in the report:

```
assert -1900 == 80.0
```

The system found a real bug in code it had never seen, wrote the test that
proves it, and correctly called it a defect rather than a bad test.

---

## Running it on a real repository

```bash
git clone https://github.com/psf/requests.git /tmp/requests
python run_pipeline.py /tmp/requests/src/requests
```

Without `--stage3` it stops after the risk ranking and tells you what stage 3
*would* generate tests for. That matters because stage 3 costs money — each
function is several Groq calls across three agents, throttled to about 24 per
minute.

On `requests` this analyses 266 functions and ranks `resolve_redirects` as the
riskiest, which is a fair call: it is one of the most-patched functions in
that library.

---

## Command reference

```bash
python run_pipeline.py <target> [options]
```

| Option | Meaning |
|---|---|
| `--stage3` | Run test generation. Off by default because it makes paid API calls |
| `--stage4` | Run the generated tests and evaluate them |
| `--min-risk-level {HIGH,MEDIUM,LOW}` | How far down the risk ranking to generate tests. Default MEDIUM |
| `--only {1,2,3,4}` | Run a single stage against artifacts already on disk |
| `--artifacts DIR` | Where to write output. Default `./artifacts` |
| `--no-git` | Skip git history mining. Faster, but weakens the risk scores |
| `--c1-python` … `--c4-python` | Point a stage at a specific interpreter |

Examples:

```bash
# Just analysis and risk ranking — no cost, no API calls
python run_pipeline.py ./my_project

# Re-run only the evaluation against tests already generated
python run_pipeline.py ./my_project --only 4

# Everything, including low-risk functions
python run_pipeline.py ./my_project --min-risk-level LOW --stage3 --stage4
```

---

## Where things live

```
components/          the four components, each a git subtree of its own branch
  c1_static_analysis/
  c2_ml_risk/
  c3_llm_tests/
  c4_test_eval/

pipeline/            the integration layer
  contracts.py         the JSON contract between stages
  extractors/          metrics C1 measures internally but does not emit
  stages/              orchestration for each stage
  runners/             scripts that execute inside a component's own environment

examples/            the demo project
tools/               diagnostic helpers
run_pipeline.py      the CLI
setup_pipeline.py    one-time environment setup
PIPELINE_NOTES.md    how the integration works, and every open issue found
```

---

## Known issues

`PIPELINE_NOTES.md` documents everything found while integrating, with steps
to reproduce each one. The ones that affect results most:

- **C2's committed model file is out of date.** It scores its own documented
  sample at 0.04 against a recorded 0.43. Re-running `train.py` reproduces the
  documented figure, so only the saved files need regenerating.
- **Nothing reaches the HIGH tier on real code.** The riskiest function in
  `requests` scores 0.358 against a 0.65 threshold, so the thresholds likely
  need recalibrating against real repositories rather than synthetic data.
- **C4's failure classifier over-reports "Real Defect".** It checks for the
  word `assert` before checking the actual error type, and pytest tracebacks
  nearly always contain it. `tools/c4_probe/` reproduces this.
- **C4's coverage uses the whole codebase as its denominator**, so the grade
  looks poor no matter how good the tests are.
- **C1 only reads Google-style docstrings.** Sphinx style (`:param:`,
  `:raises:`) is skipped entirely.
