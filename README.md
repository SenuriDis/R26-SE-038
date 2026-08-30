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
| `--changed-only [REF]` | Only analyse functions touched since REF. Auto-detects the base if omitted |
| `--max-functions N` | Generate tests for at most N functions, highest risk first |
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

## Running it in CI

Generating tests costs roughly 45 seconds per function on Groq's free tier,
so testing an entire repository is measured in hours. Two flags make this
practical, and they map onto the two situations a CI run is ever in.

**A pull request** — only look at what changed:

```bash
python run_pipeline.py . --changed-only --stage3 --stage4
```

Functions the diff did not touch are skipped entirely, so a typical PR
finishes in a minute or two. The base to compare against is worked out
automatically: GitHub Actions' target branch if present, otherwise the
default branch, otherwise the previous commit.

**A first run on a repository that has never been analysed** — rank
everything, but only write tests for what matters most:

```bash
python run_pipeline.py . --min-risk-level LOW --max-functions 20 --stage3 --stage4
```

This works because the stages differ enormously in cost. On a 266-function
library:

| stage | time |
|---|---|
| 1 — analysis and git history | 23s |
| 2 — risk ranking | 3m 22s |
| 3 — test generation, all 266 | **~3.5 hours** |

Ranking everything is cheap; generating tests for everything is not. So the
first run ranks the whole repository and spends its budget on the top 20,
which is roughly twenty minutes rather than several hours. After that, pull
requests keep it up to date incrementally.

Choosing what to test rather than testing everything is the point of
component 2 — the cap is that model doing the job it exists for.

> **Important for GitHub Actions:** the default checkout is a shallow clone
> with no history, and the risk model leans heavily on `bug_history` and
> `commit_frequency`. Without full history every function looks brand new and
> scores LOW. Use `fetch-depth: 0`:
>
> ```yaml
> - uses: actions/checkout@v4
>   with:
>     fetch-depth: 0
> ```
>
> If history genuinely is not available the pipeline says so and falls back to
> a full scan rather than silently analysing nothing.

---

## Using it as a GitHub Action

The pipeline is packaged as a Docker action, so the four environments are
baked into the image rather than installed on every run.

Copy `examples/ai-test-review.yml` into `.github/workflows/`, add your Groq
key as a repository secret, and open a pull request. The report appears in
the job summary and as a comment on the PR.

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0          # required -- see below

- uses: your-org/your-repo@v1
  with:
    groq-api-key: ${{ secrets.GROQ_API_KEY }}
    changed-only: "true"
    min-risk-level: "LOW"
    max-functions: "5"
```

| Input | Default | Notes |
|---|---|---|
| `groq-api-key` | — | Required. Store as a secret |
| `path` | `.` | Directory to analyse |
| `changed-only` | `true` | Only functions the PR touched |
| `max-functions` | `10` | Budget cap, highest risk first |
| `min-risk-level` | `MEDIUM` | Set to `LOW` on small repositories |
| `comment-on-pr` | `true` | Needs `pull-requests: write` |
| `fail-on-defect` | `false` | Whether a likely defect fails the check |

Two things that will silently produce an empty run:

- **`fetch-depth: 0` is not optional.** The risk model's strongest features
  are `bug_history` and `commit_frequency`. With the default shallow clone
  there is no history, so every function looks brand new and scores LOW.
- **`min-risk-level: LOW` on small repositories.** Only 1 function in 266
  reached MEDIUM on a mature library. Leaving the default on a small project
  selects nothing, and the run succeeds having done no work.

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
