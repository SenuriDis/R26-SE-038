"""
Stage 4 -- C4 test execution and evaluation.

Reads  C3's generated tests + the target's source
Writes evaluation_report.json (correctness, coverage, mutation score,
       failure classification)

C4 is built around its own sample project: `execute_tests.py` derives
SRC_DIR, TESTS_DIR and REPORTS_DIR from `BASE_DIR`, the directory the script
itself sits in, and its Dockerfile copies its own src/ and tests/ in.

Rather than modify any of that, this stage stages a working directory in
exactly the shape C4 expects and drops a copy of its script in:

    <artifacts>/c4_workdir/
        execute_tests.py   copied from C4, unmodified
        src/               the target's importable source root
        tests/             C3's generated tests
        reports/           C4's output lands here

Because BASE_DIR follows the script, every path resolves inside the workdir
and C4 runs against the target instead of its own samples.

Docker is C4's intended isolation mechanism. This stage runs locally instead,
which needs no daemon; the trade-off is that tests execute in the host
environment rather than a container.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

from pipeline import contracts

C4_ROOT = contracts.REPO_ROOT / "components" / "c4_test_eval"
C4_SCRIPT = C4_ROOT / "execute_tests.py"
WORKDIR_NAME = "c4_workdir"


class Stage4Error(RuntimeError):
    """Raised when C4 cannot be run or fails while evaluating."""


def resolve_python(explicit: Optional[str] = None) -> str:
    """Explicit flag, then C4_PYTHON, then a venv inside C4, then our own."""
    if explicit:
        return explicit

    from_env = os.environ.get("C4_PYTHON")
    if from_env:
        return from_env

    for candidate in (
        C4_ROOT / "venv" / "Scripts" / "python.exe",
        C4_ROOT / "venv" / "bin" / "python",
    ):
        if candidate.exists():
            return str(candidate)

    return sys.executable


def check_dependencies(python_exe: str) -> Optional[str]:
    """None when C4's test tooling is importable, else a human-readable reason."""
    if not Path(python_exe).exists() and not shutil.which(python_exe):
        return f"interpreter not found: {python_exe}"

    result = subprocess.run(
        [python_exe, "-c", "import pytest, pytest_cov, pytest_jsonreport, coverage"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        missing = result.stderr.strip().splitlines()[-1] if result.stderr else "unknown"
        return (
            f"{python_exe} cannot import C4's test tooling ({missing}).\n"
            f"    Install with: {python_exe} -m pip install -r "
            f"{C4_ROOT / 'requirements.txt'}"
        )
    return None


def find_generated_tests(artifact_dir: Path) -> List[Path]:
    """
    Every test file C3 produced, newest run first.

    C3 writes one directory per run, so without this the stage would evaluate
    whichever run happened to sort first rather than the latest.
    """
    output_root = artifact_dir / "c3_output"
    if not output_root.exists():
        return []

    runs = sorted(
        (p for p in output_root.iterdir() if p.is_dir() and p.name.startswith("run_")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    for run in runs:
        tests = sorted((run / "generated_tests").glob("test_*.py"))
        if tests:
            return tests

    return []


def recorded_repo_root(artifact_dir: Path) -> Optional[Path]:
    """
    The root stage 1 made file paths relative to.

    This is the only correct import root, because C3 derives its test imports
    straight from those relative paths -- `examples/demo_project/pricing.py`
    becomes `from examples.demo_project.pricing import ...`. Staging any other
    directory as the root makes every generated test fail to import.
    """
    c2_input = artifact_dir / contracts.STAGE1_C2_INPUT
    if not c2_input.exists():
        return None

    try:
        recorded = json.loads(c2_input.read_text(encoding="utf-8")).get("repo_root")
    except (ValueError, OSError):
        return None

    return Path(recorded) if recorded else None


def tested_source_files(artifact_dir: Path) -> List[str]:
    """
    The repo-relative source files holding the functions C3 actually tested.

    Used to scope both coverage and mutation. Without it C4 measures the whole
    source tree, so tests for two functions score 24% against every statement
    in the project and the grade is meaningless. Mutation is worse: it mutates
    everything, which on a real repository is thousands of mutants and never
    finishes.
    """
    run_dir = _latest_c3_run(artifact_dir)
    paths: List[str] = []

    if run_dir is not None:
        review = _load_json(run_dir / "code_review_report.json")
        if review:
            for report in review.get("reports", []):
                path = report.get("file_path")
                if path and path not in paths:
                    paths.append(path)

    # Fall back to whatever the ML report selected, in case the review is
    # missing (its agent can fail independently of test generation).
    if not paths:
        report = _load_json(artifact_dir / contracts.STAGE2_ML_OUTPUT)
        if report:
            for tier in report.get("tier_breakdown", {}).values():
                for function in tier.get("functions", []):
                    path = function.get("file_path")
                    if path and path not in paths:
                        paths.append(path)

    return paths


def _load_json(path: Path) -> Optional[Dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def _latest_c3_run(artifact_dir: Path) -> Optional[Path]:
    root = artifact_dir / "c3_output"
    if not root.exists():
        return None
    runs = sorted(
        (p for p in root.iterdir() if p.is_dir() and p.name.startswith("run_")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return runs[0] if runs else None


def write_scoping_config(workdir: Path, source_files: List[str]) -> None:
    """
    Point coverage and mutation at the tested files only.

    Both tools are configured through files C4 reads from its own directory,
    so this needs no change to C4:

      .coveragerc  read by coverage.py, narrows what --cov measures
      setup.cfg    read by mutmut; C4 only writes its own if one is absent,
                   so writing it first is how paths_to_mutate gets narrowed
    """
    if not source_files:
        return

    staged = [f"src/{path}" for path in source_files]

    (workdir / ".coveragerc").write_text(
        "[run]\nbranch = True\ninclude =\n"
        + "".join(f"    {path}\n" for path in staged),
        encoding="utf-8",
    )

    (workdir / "setup.cfg").write_text(
        "[mutmut]\n"
        f"paths_to_mutate={','.join(staged)}\n"
        "backup=False\n"
        "runner=python -m pytest\n"
        "tests_dir=tests/\n",
        encoding="utf-8",
    )


def stage_workdir(
    artifact_dir: Path,
    repo_root: Path,
    target: Path,
    tests: List[Path],
) -> Path:
    """
    Build the directory layout C4's execute_tests.py expects.

    The target is copied under `src/` at its path *relative to the repo root*,
    so a test importing `examples.demo_project.pricing` resolves once `src/` is
    on sys.path. Only the analysed subtree is copied rather than the whole
    repository, which keeps the workdir small and coverage focused.
    """
    workdir = artifact_dir / WORKDIR_NAME
    if workdir.exists():
        shutil.rmtree(workdir)

    (workdir / "reports").mkdir(parents=True)
    (workdir / "tests").mkdir()

    # C4's script, unmodified. BASE_DIR follows it here, which is what
    # repoints SRC_DIR / TESTS_DIR / REPORTS_DIR at the staged layout.
    shutil.copy2(C4_SCRIPT, workdir / "execute_tests.py")

    target = target.resolve()
    source_dir = target if target.is_dir() else target.parent

    try:
        relative = source_dir.relative_to(repo_root.resolve())
    except ValueError:
        relative = Path(".")

    destination = workdir / "src" / relative
    destination.parent.mkdir(parents=True, exist_ok=True)

    shutil.copytree(
        source_dir,
        destination,
        ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", ".git", "venv", ".venv", "node_modules",
        ),
    )

    for test_file in tests:
        shutil.copy2(test_file, workdir / "tests" / test_file.name)

    return workdir


def run(
    artifact_dir: Path,
    target: str,
    source_root: Optional[str] = None,
    python_exe: Optional[str] = None,
) -> Dict:
    """Evaluate C3's generated tests against the target's source."""
    if not C4_SCRIPT.exists():
        raise Stage4Error(f"C4's execute_tests.py not found at {C4_SCRIPT}")

    tests = find_generated_tests(artifact_dir)
    if not tests:
        raise Stage4Error(
            f"No generated tests under {artifact_dir / 'c3_output'} -- run stage 3 first."
        )

    root = (
        Path(source_root) if source_root
        else recorded_repo_root(artifact_dir)
        or Path(target).resolve()
    )
    if not root.exists():
        raise Stage4Error(f"source root does not exist: {root}")

    interpreter = resolve_python(python_exe)
    problem = check_dependencies(interpreter)
    if problem:
        raise Stage4Error(problem)

    workdir = stage_workdir(artifact_dir, root, Path(target), tests)

    scoped = tested_source_files(artifact_dir)
    write_scoping_config(workdir, scoped)

    # The staged copy has to win over any installed distribution of the same
    # package, otherwise coverage measures site-packages instead of the target.
    child_env = dict(os.environ)
    staged_src = str((workdir / "src").resolve())
    child_env["PYTHONPATH"] = os.pathsep.join(
        [staged_src] + ([child_env["PYTHONPATH"]] if child_env.get("PYTHONPATH") else [])
    )
    child_env["PYTHONIOENCODING"] = "utf-8"

    # C4 shells out to `mutmut` as a bare command. Running the venv's python
    # directly does not put that venv's Scripts/bin on PATH, so the executable
    # is not found and mutation testing silently reports zero mutants.
    scripts_dir = Path(interpreter).parent
    child_env["PATH"] = os.pathsep.join([str(scripts_dir), child_env.get("PATH", "")])

    result = subprocess.run(
        [interpreter, "execute_tests.py"],
        cwd=str(workdir),
        env=child_env,
        text=True,
    )

    report_path = workdir / "reports" / "evaluation_report.json"

    return {
        "workdir": str(workdir),
        "report": str(report_path) if report_path.exists() else None,
        "tests_evaluated": [t.name for t in tests],
        "source_root": str(root),
        "exit_code": result.returncode,
    }


def summarise(report_path: Path) -> Optional[Dict]:
    """Pull the headline numbers out of C4's evaluation report."""
    if not report_path.exists():
        return None
    try:
        return json.loads(report_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
