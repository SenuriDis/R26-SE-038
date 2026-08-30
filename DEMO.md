# Demo runbook

Two ways to demo. The GitHub Action is the one to lead with — it shows the
system as something people would actually use. The CLI is the backup.

---

## Before you start — 30 seconds

Check there is Groq budget left:

```
venv\Scripts\python.exe -c "import re;from groq import Groq;k=[re.split(r'\s#',l.split('=',1)[1].strip())[0].strip() for l in open('.env') if l.startswith('GROQ_API_KEY')][0];Groq(api_key=k).chat.completions.create(model='openai/gpt-oss-120b',messages=[{'role':'user','content':'x'*400}],max_tokens=100);print('QUOTA OK')"
```

If it errors with `TPD`, the daily cap for that model is spent. Each model has
its own allowance, so add this to the workflow to switch:

```yaml
groq-model: "openai/gpt-oss-20b"
```

**Do not rehearse repeatedly beforehand.** Every run spends from the same
daily pool, and the demo needs it.

---

## Demo A — the GitHub Action (lead with this)

```bash
cd "D:\Year 4 Sem 1\demo-repo"
git checkout main && git pull
git checkout -b live-demo
```

Open `src/cart.py`, change one line — the `apply_discount` docstring is fine.

```bash
git commit -am "Adjust discount handling"
git push -u origin live-demo
```

Open the pull request on GitHub. The Action starts on its own.

**Takes about a minute** now the environment cache is warm. Talk through the
architecture while it runs.

### What to show, in order

**1. The Actions tab** — the four stages running.

**2. The PR comment** — the whole system's output in one place:

- *Risk ranking* — `apply_discount` ranked first, reason given as `bug history`
- *Documentation gaps* — functions whose docstrings disagree with their code,
  found without executing anything
- *Generated tests* — how many, and traceability
- *Code review* — the HIGH finding naming the bug in plain English
- *Test execution* — pass rate and coverage

**3. The Files tab** — this is the moment. `tests/ai_generated/` is a new
folder the Action committed to your branch. Open the test file.

> "Nobody wrote this. The system read the code, decided this function was the
> riskiest, wrote these tests, ran them, and committed them to the pull
> request."

**4. The commit list** — `test: add AI-generated tests` from
github-actions[bot].

---

## Demo B — the CLI (backup, and useful for showing the internals)

```
python run_pipeline.py examples/demo_project --min-risk-level LOW --stage3 --stage4
```

About 2 minutes 30 seconds. Prints each stage as it goes, so you can narrate
the four components. Ends with:

```
Valid Tests    : 3          Success Rate : 100.0%
Passed         : 7          Failed       : 2
Line Coverage  : 77.78%     Branch       : 70.0%
Real Defect    : 2
```

The two failures are genuine — `examples/demo_project/pricing.py` has a
deliberate bug in `apply_discount`, and the generated test catches it with
`assert -4800 == 150.0`.

For one readable page instead of seven JSON files:

```
python -m pipeline.report artifacts
```

---

## If everything fails live

`demo_backup/` holds a complete verified run:

- `REPORT.md` — the single-page summary
- `terminal_output.log` — full terminal output
- `artifacts/` — every output file

Open `REPORT.md` and talk through it.

---

## What each component contributes

| | Who | What to point at |
|---|---|---|
| 1 | Senuri | Documentation gaps — found from docstrings alone |
| 2 | Vihanga | The ranking, and the reason column |
| 3 | Harrish | Generated tests, traceability, code review findings |
| 4 | Nisula | Pass rate, coverage, defect classification |

---

## Likely questions

**Why is everything LOW risk?**
> The model was trained on data resembling industrial defect datasets, where
> risky functions carry far more history than a small demo project. The
> ordering is right; the absolute scale needs calibrating against real
> repositories. That is part of the remaining work.

**Why only a few functions?**
> Test generation costs roughly 45 seconds per function. On a pull request we
> analyse only what changed; on a first run we rank everything and generate
> for the highest-risk few. Deciding what deserves testing is what component 2
> is for.

**Does it work on real code?**
> Yes. We ran it over the `requests` library — 266 functions. It ranked
> `resolve_redirects` riskiest, which is one of the most-patched functions in
> that codebase.

**What does not work yet?**
> Mutation testing needs Linux and currently mutates the whole codebase rather
> than the functions under test. Coverage is measured against the whole
> repository, so the grade understates things. And the risk thresholds are
> calibrated on synthetic data, so real code compresses towards LOW.

Answering that last one precisely is worth more than claiming everything
works.
