"""
Stage 1 -- C1 static analysis, plus the C1 -> C2 adapter.

Writes  01_static_analysis.json  (C1's native format, unmodified)
Writes  02_c2_input.json         (C2 BatchPredictRequest shape)

C1 runs as a subprocess so its `src.*` imports can't collide with C3's own
`src/` package. Point at its interpreter with --c1-python or C1_PYTHON.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

from pipeline import contracts

RUNNER = Path(__file__).resolve().parent.parent / "runners" / "c1_analyze.py"
SUMMARY_MARKER = "__STAGE1_SUMMARY__"


class Stage1Error(RuntimeError):
    """Raised when C1 cannot be run or fails while analysing."""


def resolve_python(explicit: Optional[str] = None) -> str:
    """Explicit flag, then C1_PYTHON, then a venv inside C1, then our own."""
    if explicit:
        return explicit

    from_env = os.environ.get("C1_PYTHON")
    if from_env:
        return from_env

    for candidate in (
        contracts.C1_ROOT / "venv" / "Scripts" / "python.exe",
        contracts.C1_ROOT / "venv" / "bin" / "python",
        contracts.C1_ROOT / ".venv" / "Scripts" / "python.exe",
        contracts.C1_ROOT / ".venv" / "bin" / "python",
    ):
        if candidate.exists():
            return str(candidate)

    return sys.executable


def run(
    target: str,
    artifact_dir: Path,
    project_name: str,
    python_exe: Optional[str] = None,
    mine_git: bool = True,
) -> Dict:
    """Analyse `target` with C1 and write both stage-1 artifacts."""
    target_path = Path(target).resolve()
    if not target_path.exists():
        raise Stage1Error(f"target does not exist: {target_path}")

    interpreter = resolve_python(python_exe)

    command = [
        interpreter,
        str(RUNNER),
        str(target_path),
        str(artifact_dir.resolve()),
        project_name,
        str(contracts.REPO_ROOT),
    ]
    if not mine_git:
        command.append("--no-git")

    result = subprocess.run(
        command,
        cwd=str(contracts.C1_ROOT),
        capture_output=True,
        text=True,
    )

    summary = None
    for line in result.stdout.splitlines():
        if line.startswith(SUMMARY_MARKER):
            summary = json.loads(line[len(SUMMARY_MARKER):])
        # C1 prints its whole formatted JSON to stdout on some paths; only the
        # summary line is of interest here, so the rest is dropped.

    if result.stderr:
        print(result.stderr, end="")

    if result.returncode != 0:
        raise Stage1Error(f"C1 exited with code {result.returncode}.")

    if summary is None:
        raise Stage1Error("C1 finished but produced no summary line.")

    summary["interpreter"] = interpreter
    return summary
