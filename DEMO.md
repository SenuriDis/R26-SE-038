# Demo runbook

Everything needed to show the four components working together.

---

## The one command

```
python run_pipeline.py examples/demo_project --min-risk-level LOW --stage3 --stage4
```

Takes **about 2 minutes 30 seconds**. Run it from
`D:\Year 4 Sem 1\Intelligent-software-testing-system`.

If `python` is not on your PATH, use the venv directly:

```
venv\Scripts\python.exe run_pipeline.py examples/demo_project --min-risk-level LOW --stage3 --stage4
```

---

## Check this before you present

```
venv\Scripts\python.exe -c "import re;from groq import Groq;k=[re.split(r'\s#',l.split('=',1)[1].strip())[0].strip() for l in open('.env') if l.startswith('GROQ_API_KEY')][0];Groq(api_key=k).chat.completions.create(model='openai/gpt-oss-20b',messages=[{'role':'user','content':'x'*400}],max_tokens=100);print('QUOTA OK')"
```

Prints `QUOTA OK` if there is budget. If it errors with `TPD` you have hit the
daily token cap — open `.env` and switch the two `GROQ_MODEL_*` lines to the
other model:

```
GROQ_MODEL_AGENT1=openai/gpt-oss-120b
GROQ_MODEL_AGENT3=openai/gpt-oss-120b
```

Each model has its own separate daily allowance, so swapping gives a fresh
budget. **Do not run the demo repeatedly beforehand** — every run spends
tokens from the same daily pool.

---

## What to say while it runs

Each stage prints as it goes, so you can narrate.

**Stage 1 — Static analysis (Senuri)**
> Parses the code, measures complexity, mines git history, and compares each
> function against its own docstring.

Point at: `documented funcs : 3 / 3`

**Stage 2 — ML risk ranking (Vihanga)**
> Scores every function for defect risk and ranks what is worth testing. We
> don't test everything — the model decides what deserves attention.

**Stage 3 — LLM test generation (you)**
> Three agents. One writes the test cases, one validates and repairs them, one
> reviews the code.

Point at: `Valid Tests : 3` and `Success Rate : 100.0%`, plus the
traceability figures `trace 3/3`.

**Stage 4 — Execution and evaluation (Nisula)**
> Runs the generated tests, measures coverage, and decides whether each
> failure is a genuine defect or a bad test.

Point at: `Real Defect : 2`

---

## The result

```
Valid Tests    : 3          Success Rate : 100.0%
Passed         : 7          Failed       : 2
Line Coverage  : 77.78%     Branch       : 70.0%

Real Defect         : 2
Invalid AI Test     : 0
Environment Failure : 0
```

The two failures are real. `examples/demo_project/pricing.py` has a deliberate
bug in `apply_discount` — it forgets to divide the percentage by 100, so 20%
off 100 returns -1900 instead of 80. The system found it, wrote the test that
proves it, and classified it as a defect rather than a broken test.

`charge` also documents a `ValueError` it never raises. Component 1 catches
that from the docstring alone, without executing anything.

---

## Showing the output

Everything lands in `artifacts/`:

```
artifacts/01_static_analysis.json     C1's measurements
artifacts/02_c2_input.json            what went to the ML model
artifacts/03_ml_output.json           the risk ranking
artifacts/04_spec_contract.json       documentation vs code
artifacts/c3_output/run_*/            the generated tests
artifacts/c4_workdir/reports/         coverage and defect report
```

For one readable page instead of seven JSON files:

```
python -m pipeline.report artifacts
```

Worth opening `artifacts/c3_output/run_*/generated_tests/` in the editor — the
generated test files are the most tangible thing to show.

---

## If it fails live

`demo_backup/` holds a complete successful run:

- `REPORT.md` — the single-page summary
- `terminal_output.log` — the full terminal output
- `artifacts/` — every output file

Open `demo_backup/REPORT.md` and talk through it. Same content, already
verified.

---

## Likely questions

**Why is everything LOW risk?**
> The model was trained on data resembling industrial defect datasets, where
> risky functions have far more history than a small demo project. Threshold
> calibration against real repositories is part of the remaining work. The
> ranking still orders correctly — it just compresses the absolute scores.

**Why only three functions?**
> Test generation costs roughly 45 seconds per function, so we scope it. On a
> pull request we analyse only the functions that changed; on a first run we
> rank everything and generate for the highest-risk few.

**Does it work on real code?**
> Yes — we ran it on the `requests` library, 266 functions. It ranked
> `resolve_redirects` riskiest, which is one of the most-patched functions in
> that codebase.

**What is left to do?**
> Threshold calibration, mutation testing on Windows, and packaging it as a
> GitHub Action so it runs automatically on pull requests.
