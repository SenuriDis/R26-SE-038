"""
Runs C1's static analysis and the C1 -> C2 adapter. Executed inside C1's own
environment, with C1's root as cwd and sys.path[0].

    python c1_analyze.py <target> <artifact_dir> <project_name> <repo_root>

Writes two artifacts:

    01_static_analysis.json   C1's native per-file output, unmodified
    02_c2_input.json          the same functions flattened into C2's
                              BatchPredictRequest shape

C1's source is imported and reused as-is. The only thing added here is the
eight AST fields C1 measures internally but never writes out, and the
flattening from per-file to per-function.
"""

import ast
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Mirrors the ignore set inside C1's analyze_folder(). C1 defines it inline
# rather than exporting it, so a change there needs the same change here.
IGNORED_FOLDERS = {"__pycache__", ".git", "venv", "migrations", "tests"}


def iter_python_files(target: Path) -> List[Path]:
    """C1's traversal rule: .py files, skipping dunder files and ignored dirs."""
    if target.is_file():
        return [target]

    found = []
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in IGNORED_FOLDERS]
        for name in files:
            if name.endswith(".py") and not name.startswith("__"):
                found.append(Path(root) / name)
    return sorted(found)


def functions_for_file(file_path: Path, c2_defaults: Dict) -> Tuple[List[Dict], List[str]]:
    """
    Build one C2 function record per function in `file_path`.

    Returns (records, skipped_async). Async functions are reported rather than
    dropped silently: C1's calculators only visit ast.FunctionDef, so an async
    def would come through with no complexity and no dependencies.
    """
    from src.parser.ast_parser import parse_python_file
    from src.extractor.dependency_extractor import DependencyExtractor
    from src.metrics.function_complexity_calculator import FunctionComplexityCalculator
    from src.adapter.function_info_adapter import FunctionInfoAdapter

    from pipeline.extractors import function_metrics

    tree, _source = parse_python_file(str(file_path))
    if tree is None:
        return [], []

    complexities = FunctionComplexityCalculator().extract(tree)
    dependencies = DependencyExtractor().extract(tree)
    function_infos = FunctionInfoAdapter().build(tree, complexities, dependencies)

    records = []
    for info in function_infos:
        records.append({
            # ── straight from C1 ──
            "function_name": info.name,
            "file_path": str(file_path),
            "cyclomatic_complexity": info.cyclomatic_complexity,
            "nesting_depth": info.nesting_depth,
            "lines_of_code": info.lines_of_code,
            "dependencies": list(info.dependencies),
            "fan_out": info.dependency_count,

            # ── derived from the AST node C1 already holds ──
            **function_metrics.extract(info.ast_node),

            # ── nothing upstream produces these yet ──
            **c2_defaults,
        })

    skipped_async = [
        node.name for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef)
    ]

    return records, skipped_async


def main() -> int:
    if len(sys.argv) < 5:
        print(__doc__)
        return 2

    target = Path(sys.argv[1]).resolve()
    artifact_dir = Path(sys.argv[2]).resolve()
    project_name = sys.argv[3]
    repo_root = Path(sys.argv[4]).resolve()

    # Python puts *this script's* directory on sys.path, not the cwd, so C1's
    # root has to be added explicitly for its `src.*` and `main` imports.
    # It goes first so `src` always resolves to C1's package.
    c1_root = str(Path.cwd())
    if c1_root not in sys.path:
        sys.path.insert(0, c1_root)

    # The orchestrator's package lives at the repo root, not inside C1.
    # Appended, not inserted, so it can never shadow C1's own modules.
    if str(repo_root) not in sys.path:
        sys.path.append(str(repo_root))

    from pipeline.contracts import STAGE1_RAW, STAGE1_C2_INPUT, C2_DEFAULTS

    artifact_dir.mkdir(parents=True, exist_ok=True)

    # ── artifact 01: C1's own output, untouched ──────────────────────────────
    from main import analyze_file, analyze_folder

    if target.is_file():
        raw = [r for r in [analyze_file(str(target))] if r]
    else:
        raw = analyze_folder(str(target))

    raw_path = artifact_dir / STAGE1_RAW
    raw_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")

    # ── artifact 02: flattened + enriched for C2 ─────────────────────────────
    all_records: List[Dict] = []
    all_skipped: List[str] = []

    for py_file in iter_python_files(target):
        records, skipped = functions_for_file(py_file, C2_DEFAULTS)
        all_records.extend(records)
        all_skipped.extend(skipped)

    c2_input_path = artifact_dir / STAGE1_C2_INPUT
    c2_input_path.write_text(
        json.dumps({"project_name": project_name, "functions": all_records}, indent=2),
        encoding="utf-8",
    )

    # Summary goes back to the orchestrator over stdout as a JSON line.
    print("__STAGE1_SUMMARY__" + json.dumps({
        "files_analyzed": len(raw),
        "functions_extracted": len(all_records),
        "async_functions_skipped": all_skipped,
        "raw_artifact": str(raw_path),
        "c2_input_artifact": str(c2_input_path),
    }))

    return 0


if __name__ == "__main__":
    sys.exit(main())
