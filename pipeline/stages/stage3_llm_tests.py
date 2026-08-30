"""
Stage 3 -- C3 LLM test generation and code review.

Reads  03_ml_output.json  (C2's tier_breakdown)
Writes generated tests + review reports under the run's output directory.

Unlike stages 1 and 2, C3 already ships a complete CLI, so this stage is a
thin wrapper around `components/c3_llm_tests/run_pipeline.py` rather than a
runner of its own.

Two things make this stage different from the others:

- **It costs money.** All three agents call Groq. `preview()` reports how many
  functions qualify before anything is spent.
- **Credentials.** C3 resolves `.env` relative to its cwd, which is its own
  directory once vendored. Rather than copying secrets into the vendored tree
  (where they could be committed by accident), the repo-root `.env` is parsed
  and passed through the subprocess environment. Environment variables take
  precedence over the file in pydantic-settings, so this works unchanged.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

from pipeline import contracts

C3_ROOT = contracts.REPO_ROOT / "components" / "c3_llm_tests"
C3_CLI = C3_ROOT / "run_pipeline.py"

_TIER_ORDER = ["HIGH", "MEDIUM", "LOW"]


class Stage3Error(RuntimeError):
    """Raised when C3 cannot be run or fails while generating."""


def _parse_env_value(raw: str) -> str:
    """
    Read one .env value the way python-dotenv does.

    Quoted values keep everything inside the quotes. Unquoted values end at an
    inline comment, which is a '#' preceded by whitespace.

    This matters more than it looks. The repo's .env carries
    `CHROMA_DB_PATH=./data/chroma_db #Where to store the chunks`, and env vars
    outrank the .env file in pydantic-settings. Passing the comment through
    made C3 create a directory literally named 'chroma_db #Where to store the
    chunks'.
    """
    value = raw.strip()
    if not value:
        return ""

    if value[0] in "\"'":
        quote = value[0]
        closing = value.find(quote, 1)
        if closing != -1:
            return value[1:closing]
        return value[1:]

    comment = re.search(r"\s#", value)
    if comment:
        value = value[:comment.start()]

    return value.strip()


def load_root_env() -> Dict[str, str]:
    """Parse the repo-root .env into a plain dict of KEY -> value."""
    env_path = contracts.REPO_ROOT / ".env"
    if not env_path.exists():
        return {}

    values = {}
    for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = _parse_env_value(value)

    return values


def resolve_python(explicit: Optional[str] = None) -> str:
    """Explicit flag, then C3_PYTHON, then the repo venv, then our own."""
    if explicit:
        return explicit

    from_env = os.environ.get("C3_PYTHON")
    if from_env:
        return from_env

    # C3's dependencies are what the repo's own venv was built for.
    for candidate in (
        contracts.REPO_ROOT / "venv" / "Scripts" / "python.exe",
        contracts.REPO_ROOT / "venv" / "bin" / "python",
    ):
        if candidate.exists():
            return str(candidate)

    return sys.executable


def preview(artifact_dir: Path, min_risk_level: str = "MEDIUM",
            max_functions: Optional[int] = None) -> Dict:
    """
    What stage 3 would process, without spending anything.

    Returns tier counts and the functions at or above `min_risk_level`.
    """
    report_path = artifact_dir / contracts.STAGE2_ML_OUTPUT
    if not report_path.exists():
        raise Stage3Error(f"{report_path} is missing -- run stage 2 first.")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    tiers = report.get("tier_breakdown", {})

    cutoff = _TIER_ORDER.index(min_risk_level.upper())
    selected: List[Dict] = []
    counts = {}

    for index, tier in enumerate(_TIER_ORDER):
        functions = tiers.get(tier, {}).get("functions", [])
        counts[tier] = len(functions)
        if index <= cutoff:
            selected.extend(functions)

    # Highest risk first, so a budget cap keeps the functions that matter.
    selected.sort(key=lambda f: f.get("risk_score", 0.0), reverse=True)

    total_eligible = len(selected)
    capped = max_functions is not None and total_eligible > max_functions
    if capped:
        selected = selected[:max_functions]

    return {
        "counts": counts,
        "selected": selected,
        "total_eligible": total_eligible,
        "capped": capped,
        "min_risk_level": min_risk_level.upper(),
        "report_path": str(report_path),
    }


def recorded_repo_root(artifact_dir: Path) -> Optional[str]:
    """
    The root stage 1 made file paths relative to.

    C3 resolves source as `repo_path / file_path`, so its --repo-path has to be
    the same root stage 1 used. Passing the analysis target instead breaks that
    join whenever the target is a subdirectory.
    """
    c2_input = artifact_dir / contracts.STAGE1_C2_INPUT
    if not c2_input.exists():
        return None

    try:
        return json.loads(c2_input.read_text(encoding="utf-8")).get("repo_root")
    except (ValueError, OSError):
        return None


def check_credentials() -> Optional[str]:
    """None when C3 has what it needs, else a human-readable reason."""
    env = load_root_env()
    key = env.get("GROQ_API_KEY", "").strip()

    if not key or key == "placeholder":
        return (
            "GROQ_API_KEY is not set in the repo-root .env. All three C3 agents "
            "call Groq, so stage 3 cannot run without it."
        )
    return None


def write_capped_report(artifact_dir: Path, plan: Dict) -> Path:
    """
    Write a trimmed copy of the ML report holding only the selected functions.

    C3 takes a risk *level*, not a count, so a budget cap has to be applied by
    narrowing what the report contains. The original is left untouched -- this
    is a sibling file, so the full ranking is still there to look at.
    """
    original = json.loads(
        (artifact_dir / contracts.STAGE2_ML_OUTPUT).read_text(encoding="utf-8")
    )

    keep = {(f["function_name"], f["file_path"]) for f in plan["selected"]}

    tiers = {}
    for tier, block in original.get("tier_breakdown", {}).items():
        functions = [
            f for f in block.get("functions", [])
            if (f["function_name"], f["file_path"]) in keep
        ]
        tiers[tier] = {**block, "functions": functions}

    capped = {
        **original,
        "tier_breakdown": tiers,
        "ranked_functions": plan["selected"],
        "_capped_from": original.get("summary", {}).get("total_functions"),
    }

    path = artifact_dir / "03_ml_output_capped.json"
    path.write_text(json.dumps(capped, indent=2), encoding="utf-8")
    return path


def run(
    artifact_dir: Path,
    repo_path: str,
    min_risk_level: str = "MEDIUM",
    output_dir: Optional[Path] = None,
    python_exe: Optional[str] = None,
    force_reindex: bool = False,
    max_functions: Optional[int] = None,
) -> Dict:
    """Run C3 over stage 2's report."""
    if not C3_CLI.exists():
        raise Stage3Error(f"C3 CLI not found at {C3_CLI}")

    problem = check_credentials()
    if problem:
        raise Stage3Error(problem)

    report_path = (artifact_dir / contracts.STAGE2_ML_OUTPUT).resolve()
    if not report_path.exists():
        raise Stage3Error(f"{report_path} is missing -- run stage 2 first.")

    if max_functions is not None:
        plan = preview(artifact_dir, min_risk_level, max_functions)
        if plan["capped"]:
            report_path = write_capped_report(artifact_dir, plan).resolve()

    destination = (output_dir or (artifact_dir / "c3_output")).resolve()
    destination.mkdir(parents=True, exist_ok=True)

    interpreter = resolve_python(python_exe)

    # C3's settings read .env relative to cwd, which is C3's own directory.
    # Passing the root .env through the environment avoids copying secrets
    # into the vendored tree.
    child_env = dict(os.environ)
    child_env.update(load_root_env())

    # C3's summary printer emits emoji. On Windows the default console codec is
    # cp1252, which cannot encode them, and it raises UnicodeEncodeError *after*
    # every output file has already been written -- so the run looks failed when
    # it actually succeeded. Forcing UTF-8 on the child fixes it without
    # touching the vendored code.
    child_env["PYTHONIOENCODING"] = "utf-8"

    command = [
        interpreter,
        str(C3_CLI),
        "--repo-path", str(Path(repo_path).resolve()),
        "--ml-report", str(report_path),
        "--output-dir", str(destination),
        "--min-risk-level", min_risk_level.upper(),
    ]
    if force_reindex:
        command.append("--force-reindex")

    result = subprocess.run(
        command,
        cwd=str(C3_ROOT),
        env=child_env,
        text=True,
    )

    if result.returncode != 0:
        raise Stage3Error(f"C3 exited with code {result.returncode}.")

    return {"output_dir": str(destination)}
