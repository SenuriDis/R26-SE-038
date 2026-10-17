# Test Execution and Evaluation Component
**Project:** LLM and ML Enhanced Software Testing System for Automatic Test Case Generation and Code Quality Review  
**Student:** Premaratne R.A.N.C — IT22050908  
**Project ID:** R26-SE-038

---

## Overview

C4 evaluates AI-generated pytest tests by executing them, measuring coverage,
running mutation testing when the baseline passes, and producing a structured
JSON report and dashboard.

- Runs locally and in GitHub Actions through the same Docker entry point.
- Applies deterministic rules to classify failures without treating assertion
  mismatches as confirmed defects.
- Records structured failure evidence for each failed test.
- Calculates an equal-weight quality grade from pass rate, statement coverage,
  and mutation score.

## Failure Classification Rules

| Rule | Classification | Meaning |
|---|---|---|
| Syntax or indentation error points to a generated test file | `Invalid AI Test` | Python could not parse the generated test. |
| A known missing-dependency or execution-environment marker is present | `Environment Failure` | The test run may be blocked by its environment. |
| An assertion fails | `Needs Review` | The traceback alone cannot establish whether the expectation or implementation is wrong. |
| No conclusive rule matches | `Needs Review` | A person should inspect the failure evidence. |

These are explicit rules, not a learned classifier. C4 does not label an
assertion mismatch as a confirmed product defect.

## Quality Grading Model

The quality score is the equal-weight arithmetic mean:

`(pass rate + statement coverage + mutation score) / 3`

Grades are A (90–100), B (75–<90), C (60–<75), and D (<60). A grade is
unavailable if any required metric—particularly mutation score—is unavailable.
C4 does not silently substitute zero or change to a two-metric formula.
Branch and function coverage are reported separately and are not included in
this grade.

## Structured Failure Evidence

Each failed-test record in `evaluation_report.json` includes its classification
rule and reason, failure phase (`setup`, `call`, or `teardown`), exception type,
concise message, source location when pytest provides one, and up to 20,000
characters of traceback. The dashboard shows the concise evidence and provides
an expandable traceback.

## Run C4 Locally

Docker Desktop or Docker Engine must be running. From
`components/c4_test_eval/`, run:

```bash
python run.py
```

The orchestrator builds the evaluator image and runs it with networking
disabled, Linux capabilities dropped, no-new-privileges enabled, and CPU,
memory, process, and temporary-storage limits. Evaluation dependencies are
installed in the image. Reports persist under `reports/`.

### Start the C4 API and dashboard

Install backend dependencies:

```bash
npm install
```

Install frontend dependencies:

```bash
cd frontend
npm install
```

Start the backend:

```bash
node server.js
```

Start the frontend in another terminal:

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**.

### Run tests directly without Docker

This is for local debugging only and does not use the isolated environment:

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

## Reports and CI

Reports are written to `reports/`: `evaluation_report.json`,
`pytest_results.json`, `coverage.json`, `execution.log`, and `mutation.log`.
The repository-level workflow at `.github/workflows/c4-evaluate.yml` invokes
this component's `run.py` on pushes and pull requests affecting C4, so CI uses
the same Docker isolation as a local C4 run and uploads reports even if test
execution fails.

Mutation testing is skipped when the baseline has failures or no passing tests.
The mutation score is killed mutants divided by conclusively scored killed plus
survived mutants. Timeouts, suspicious, skipped, and otherwise unscored mutants
are reported separately.

## Technologies Used

| Tool | Purpose |
|------|---------|
| Python 3.10+ | Evaluation implementation |
| PyTest | Test execution framework |
| Coverage.py | Code coverage measurement |
| pytest-json-report | Structured pytest output |
| mutmut | Mutation testing |
| Docker | Isolated test execution |
| JSON | Structured evaluation and CI report |
