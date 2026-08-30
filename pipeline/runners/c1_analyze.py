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

import argparse
import ast
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Mirrors the ignore set inside C1's analyze_folder(). C1 defines it inline
# rather than exporting it, so a change there needs the same change here.
IGNORED_FOLDERS = {"__pycache__", ".git", "venv", "migrations", "tests"}


def find_repo_root(target: Path) -> Path:
    """
    The root that file paths should be expressed relative to.

    C3 treats file_path as repo-relative (`repo_path / file_path`) and, more
    importantly, embeds it verbatim into its RAG query text. An absolute
    Windows path there drags drive letters and temp-directory noise into the
    embedding and wrecks retrieval, so paths must stay short and meaningful.

    Prefers the git root, which is what C3's own demos assume
    ("src/requests/utils.py"), and falls back to the target itself.
    """
    import subprocess

    start = target if target.is_dir() else target.parent
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(start), capture_output=True, text=True, timeout=15,
        )
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        pass

    return start


def relative_path(file_path: Path, repo_root: Path) -> str:
    """
    `file_path` relative to `repo_root`, POSIX-style.

    Forward slashes because the string ends up inside an embedding query, and
    backslashes tokenise badly.
    """
    try:
        return file_path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return file_path.name


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


def functions_for_file(file_path: Path, c2_defaults: Dict, miner=None,
                       repo_root: Path = None,
                       changed_spans: List[Tuple[int, int]] = None) -> Tuple[List[Dict], List[str]]:
    """
    Build one C2 function record per function in `file_path`.

    `miner`, when given, supplies the four git-history fields per function;
    without it those stay at C2's defaults.

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

    from pipeline.extractors import git_diff

    records = []
    for info in function_infos:
        derived = function_metrics.extract(info.ast_node)

        # In diff-scoped mode, keep only functions the change actually touched.
        if changed_spans is not None:
            span = (derived["start_line"], derived["end_line"])
            if not git_diff.overlaps(span, changed_spans):
                continue

        # fan_in is the one field still without a source; it needs a
        # cross-file call graph.
        process_metrics = dict(c2_defaults)
        if miner is not None:
            process_metrics.update(
                miner.mine(file_path, derived["start_line"], derived["end_line"])
            )

        records.append({
            # ── straight from C1 ──
            "function_name": info.name,
            "file_path": (
                relative_path(file_path, repo_root)
                if repo_root is not None else str(file_path)
            ),
            "cyclomatic_complexity": info.cyclomatic_complexity,
            "nesting_depth": info.nesting_depth,
            "lines_of_code": info.lines_of_code,
            "dependencies": list(info.dependencies),
            "fan_out": info.dependency_count,

            # ── derived from the AST node C1 already holds ──
            **derived,

            # ── mined from git history, or defaults ──
            **process_metrics,
        })

    skipped_async = [
        node.name for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef)
    ]

    return records, skipped_async


def collect_function_names(paths: List[Path]) -> set:
    """
    Every function name across the whole target, for the README pass.

    A README describes the project, not one file, so C1 parses it once and
    matches it against all known function names. Mirrors the first pass in
    C1's analyze_folder_with_auto_requirements().
    """
    from src.parser.ast_parser import parse_python_file

    names = set()
    for path in paths:
        tree, _ = parse_python_file(str(path))
        if tree is None:
            continue
        names.update(
            node.name for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        )
    return names


def spec_records_for_file(file_path: Path, readme_requirements: Dict,
                          repo_root: Path = None) -> List[Dict]:
    """
    The documented contract for each function in `file_path`.

    C1's FeatureMatrixBuilder computes all of this but only emits counts and
    booleans from it -- the Requirement itself, which holds the actual
    parameter constraints and declared exceptions, is dropped. Those are the
    parts worth having downstream ("raises ValueError when amount < 0" is a
    test case; "exception_requirements_count: 1" is not), so the mapper is
    called directly here to keep them.

    Reuses C1's modules unchanged; nothing in C1 is modified.
    """
    from src.parser.ast_parser import parse_python_file
    from src.extractor.dependency_extractor import DependencyExtractor
    from src.metrics.function_complexity_calculator import FunctionComplexityCalculator
    from src.adapter.function_info_adapter import FunctionInfoAdapter
    from src.requirement_analysis.composite_extractor import CompositeRequirementExtractor
    from src.requirement_analysis.code_requirement_mapper import CodeRequirementMapper
    from src.requirement_analysis.gap_detector import GapDetector
    from src.requirement_analysis.specification_metrics import SpecificationMetricsCalculator

    from dataclasses import asdict

    tree, _source = parse_python_file(str(file_path))
    if tree is None:
        return []

    complexities = FunctionComplexityCalculator().extract(tree)
    dependencies = DependencyExtractor().extract(tree)
    function_infos = FunctionInfoAdapter().build(tree, complexities, dependencies)

    # Docstrings > README > type hints, richest wins -- C1's own precedence.
    requirements = CompositeRequirementExtractor().extract(tree, readme_requirements)

    mappings = CodeRequirementMapper().map(function_infos, requirements)

    gap_detector = GapDetector()
    spec_calculator = SpecificationMetricsCalculator()

    records = []
    for mapping in mappings:
        gaps = gap_detector.detect(mapping)
        spec_metrics = spec_calculator.calculate(mapping, gaps)

        records.append({
            # Join key onto the ML report.
            "function_name": mapping.function_name,
            "file_path": (
                relative_path(file_path, repo_root)
                if repo_root is not None else str(file_path)
            ),

            "mapping_status": mapping.status.value,

            # The part FeatureMatrixBuilder drops: the actual contract.
            "requirement": (
                mapping.requirement.to_dict()
                if mapping.requirement is not None else None
            ),

            "specification_metrics": asdict(spec_metrics),
            "gap_analysis": asdict(gaps),
        })

    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="C1 analysis + the C1->C2 adapter.")
    parser.add_argument("target")
    parser.add_argument("artifact_dir")
    parser.add_argument("project_name")
    parser.add_argument("pipeline_root")
    parser.add_argument("--no-git", action="store_true")
    parser.add_argument(
        "--changed-only",
        nargs="?",
        const="",
        default=None,
        help="Only analyse functions touched since a base ref. Empty means "
             "auto-detect the base.",
    )
    args = parser.parse_args()

    target = Path(args.target).resolve()
    artifact_dir = Path(args.artifact_dir).resolve()
    project_name = args.project_name

    # The *pipeline's* root, used only to import the pipeline package. Distinct
    # from the *target's* root computed below, which file paths are made
    # relative to.
    pipeline_root = Path(args.pipeline_root).resolve()

    # Python puts *this script's* directory on sys.path, not the cwd, so C1's
    # root has to be added explicitly for its `src.*` and `main` imports.
    # It goes first so `src` always resolves to C1's package.
    c1_root = str(Path.cwd())
    if c1_root not in sys.path:
        sys.path.insert(0, c1_root)

    # The orchestrator's package lives at the pipeline root, not inside C1.
    # Appended, not inserted, so it can never shadow C1's own modules.
    if str(pipeline_root) not in sys.path:
        sys.path.append(str(pipeline_root))

    from pipeline.contracts import (
        STAGE1_RAW, STAGE1_C2_INPUT, STAGE1_SPEC, C2_DEFAULTS,
    )
    from pipeline.extractors.git_history import GitHistoryMiner
    from pipeline.extractors import git_diff

    mine_git = not args.no_git
    miner = GitHistoryMiner(target) if mine_git else None

    # Everything downstream refers to files relative to this. C3 both joins it
    # against its --repo-path and embeds it in RAG query text, so it has to be
    # a short, meaningful path rather than an absolute one.
    repo_root = find_repo_root(target)

    # ── diff scoping ─────────────────────────────────────────────────────────
    # Falls back to a full scan rather than failing: a shallow clone or a repo
    # with one commit has nothing to diff against, and analysing everything is
    # a far better outcome there than analysing nothing.
    changed_ranges = None
    diff_note = None

    if args.changed_only is not None:
        base_ref = git_diff.resolve_base_ref(repo_root, args.changed_only or None)
        if base_ref is None:
            diff_note = "no base ref found (shallow clone?) -- analysing everything"
        else:
            try:
                changed_ranges = git_diff.changed_line_ranges(repo_root, base_ref)
                diff_note = f"diffed against {base_ref}"
                if not changed_ranges:
                    diff_note = f"no Python changes against {base_ref}"
            except git_diff.DiffUnavailable as error:
                diff_note = f"{error} -- analysing everything"

    artifact_dir.mkdir(parents=True, exist_ok=True)

    # ── artifact 01: C1's own output, untouched ──────────────────────────────
    # The *_with_auto_requirements variants are used so C1's documentation
    # analysis actually runs. C1 built them for exactly this case: cloned
    # third-party repos, where no hand-written requirement file exists and the
    # docstrings themselves are the specification.
    from main import (
        analyze_file_with_auto_requirements,
        analyze_folder_with_auto_requirements,
    )

    if target.is_file():
        raw = [r for r in [analyze_file_with_auto_requirements(str(target))] if r]
    else:
        raw = analyze_folder_with_auto_requirements(str(target))

    raw_path = artifact_dir / STAGE1_RAW
    raw_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")

    python_files = iter_python_files(target)

    if changed_ranges is not None:
        touched = git_diff.changed_files(changed_ranges, repo_root)
        python_files = [f for f in python_files if f.resolve() in touched]

    # ── artifact 04: the documented contract, for C3 ─────────────────────────
    # Built before artifact 02 so a failure here surfaces before the expensive
    # git mining runs.
    from src.requirement_analysis.readme_extractor import ReadmeRequirementExtractor

    project_root = target if target.is_dir() else target.parent
    readme_requirements = {
        r.function_name: r
        for r in ReadmeRequirementExtractor().extract(
            str(project_root), collect_function_names(python_files)
        )
    }

    spec_records: List[Dict] = []
    for py_file in python_files:
        spec_records.extend(spec_records_for_file(py_file, readme_requirements, repo_root))

    documented = sum(1 for r in spec_records if r["requirement"] is not None)

    spec_path = artifact_dir / STAGE1_SPEC
    spec_path.write_text(
        json.dumps({
            "project_name": project_name,
            "repo_root": str(repo_root),
            "readme_requirements_found": len(readme_requirements),
            "functions": spec_records,
        }, indent=2),
        encoding="utf-8",
    )

    # ── artifact 02: flattened + enriched for C2 ─────────────────────────────
    all_records: List[Dict] = []
    all_skipped: List[str] = []

    for py_file in python_files:
        spans = None
        if changed_ranges is not None:
            spans = changed_ranges.get(relative_path(py_file, repo_root), [])

        records, skipped = functions_for_file(
            py_file, C2_DEFAULTS, miner, repo_root, spans
        )
        all_records.extend(records)
        all_skipped.extend(skipped)

    c2_input_path = artifact_dir / STAGE1_C2_INPUT
    c2_input_path.write_text(
        json.dumps({
            "project_name": project_name,
            # file_path values below are relative to this.
            "repo_root": str(repo_root),
            "functions": all_records,
        }, indent=2),
        encoding="utf-8",
    )

    # Summary goes back to the orchestrator over stdout as a JSON line.
    print("__STAGE1_SUMMARY__" + json.dumps({
        "files_analyzed": len(raw),
        "functions_extracted": len(all_records),
        "async_functions_skipped": all_skipped,
        "raw_artifact": str(raw_path),
        "c2_input_artifact": str(c2_input_path),
        "spec_artifact": str(spec_path),
        "repo_root": str(repo_root),
        "diff": {
            "enabled": args.changed_only is not None,
            "note": diff_note,
            "changed_files": len(changed_ranges) if changed_ranges is not None else None,
        },
        "spec": {
            "functions": len(spec_records),
            "documented": documented,
            "readme_requirements": len(readme_requirements),
        },
        "git": {
            "enabled": mine_git,
            "repo_root": str(miner.repo_root) if miner and miner.repo_root else None,
            **(miner.stats if miner else {}),
        },
    }))

    return 0


if __name__ == "__main__":
    sys.exit(main())
