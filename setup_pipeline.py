#!/usr/bin/env python
"""
One-time setup for the integration pipeline.

    python setup_pipeline.py

Builds the three virtual environments the pipeline needs and reports anything
it cannot do for you (chiefly API keys).

Why three environments rather than one: the components pin conflicting
dependencies. C2 needs numpy 1.26, which has no Python 3.13 wheels, while C3
is built around chromadb and needs a much newer numpy. They cannot share an
interpreter, so each stage runs as a subprocess against its own.

    venv/                            C3 + the orchestrator   (any Python 3.11+)
    components/c2_ml_risk/venv/      C2's ML stack           (Python 3.12)
    components/c4_test_eval/venv/    C4's test tooling       (Python 3.12)
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent

C2_ROOT = REPO / "components" / "c2_ml_risk"
C3_ROOT = REPO / "components" / "c3_llm_tests"
C4_ROOT = REPO / "components" / "c4_test_eval"

# C2 imports only these three. Its requirements.txt also lists xgboost, shap,
# imbalanced-learn, jupyter, matplotlib and seaborn, none of which appear in
# any import -- "xgb_model" is really an sklearn GradientBoostingClassifier.
C2_PACKAGES = ["numpy==1.26.4", "pandas==2.2.1", "scikit-learn==1.4.2"]

WINDOWS = os.name == "nt"


def venv_python(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts/python.exe" if WINDOWS else "bin/python")


def find_python312(explicit=None) -> str:
    """
    Locate a Python 3.12 interpreter for C2 and C4.

    3.12 specifically: C2 pins numpy 1.26.4, which publishes no wheels for
    3.13, and its model pickle was written by scikit-learn 1.4.2 which has the
    same ceiling.
    """
    if explicit:
        return explicit

    candidates = []
    if WINDOWS:
        candidates += [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Python/Python312/python.exe",
            Path("C:/Python312/python.exe"),
        ]
    candidates += [Path("/usr/bin/python3.12"), Path("/usr/local/bin/python3.12")]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    # The py launcher, if it knows about 3.12.
    try:
        out = subprocess.run(["py", "-3.12", "-c", "import sys; print(sys.executable)"],
                             capture_output=True, text=True, timeout=20)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass

    return ""


def build(name: str, venv_dir: Path, base_python: str, packages=None, requirements=None) -> bool:
    """Create one venv and install into it. Returns True on success."""
    print(f"\n[{name}] {venv_dir.relative_to(REPO)}")

    python = venv_python(venv_dir)
    if python.exists():
        print("  already present, skipping creation")
    else:
        print(f"  creating with {base_python}")
        result = subprocess.run([base_python, "-m", "venv", str(venv_dir)],
                                capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  FAILED: {result.stderr.strip()[:200]}")
            return False

    install = [str(python), "-m", "pip", "install", "--quiet"]
    if requirements:
        install += ["-r", str(requirements)]
        print(f"  installing from {requirements.name}")
    else:
        install += list(packages)
        print(f"  installing {', '.join(packages)}")

    result = subprocess.run(install, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FAILED: {result.stderr.strip()[:400]}")
        return False

    print("  ok")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Set up the pipeline environments.")
    parser.add_argument("--python312", default=None,
                        help="Path to a Python 3.12 interpreter for C2 and C4.")
    args = parser.parse_args()

    print("=" * 62)
    print("  R26-SE-038 integration pipeline — setup")
    print("=" * 62)

    py312 = find_python312(args.python312)
    if not py312:
        print(
            "\nPython 3.12 not found. C2 and C4 need it: C2 pins numpy 1.26.4,\n"
            "which has no wheels for 3.13.\n\n"
            "  Install from https://www.python.org/downloads/release/python-31210/\n"
            "  then re-run, or pass --python312 <path>."
        )
        return 1

    print(f"\nPython 3.12 : {py312}")
    print(f"This Python : {sys.executable}")

    ok = True

    # C3 and the orchestrator share the root venv.
    ok &= build("C3 + orchestrator", REPO / "venv", sys.executable,
                requirements=C3_ROOT / "requirements.txt")

    ok &= build("C2 ML stack", C2_ROOT / "venv", py312, packages=C2_PACKAGES)

    ok &= build("C4 test tooling", C4_ROOT / "venv", py312,
                requirements=C4_ROOT / "requirements.txt")

    print("\n" + "=" * 62)

    env_file = REPO / ".env"
    if env_file.exists():
        print("  .env found")
    else:
        print(
            "  .env NOT found — stage 3 will not run without it.\n"
            "  Create one at the repo root containing at least:\n\n"
            "      GROQ_API_KEY=your_key_here\n"
        )
        ok = False

    if ok:
        print("\n  Setup complete. Try:\n")
        print("      python run_pipeline.py examples/demo_project --min-risk-level LOW\n")
    else:
        print("\n  Setup incomplete — see the messages above.\n")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
