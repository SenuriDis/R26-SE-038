#!/usr/bin/env python
"""
End-to-end pipeline for R26-SE-038.

    python run_pipeline.py <target> [options]

`target` is a Python file or a directory to analyse.

Stages, and the artifact each one leaves behind:

    1  C1 static analysis   -> artifacts/01_static_analysis.json
       C1 -> C2 adapter     -> artifacts/02_c2_input.json
    2  C2 ML risk scoring   -> artifacts/03_ml_output.json
    3  C3 LLM test gen         [not wired yet -- reads 03_ml_output.json]

Each stage reads and writes JSON on disk, so any stage can be re-run on its own
against the previous stage's output (see --only).

Components pin conflicting dependencies, so each stage runs as a subprocess
against its own interpreter. Set them with --c1-python / --c2-python or the
C1_PYTHON / C2_PYTHON environment variables.
"""

import argparse
import json
import sys
from pathlib import Path

from pipeline import contracts
from pipeline.stages import stage1_static_analysis, stage2_ml_risk


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Run the R26-SE-038 integration pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "target",
        help="Python file or directory to analyse.",
    )
    parser.add_argument(
        "--project-name",
        default=None,
        help="Project label carried through to C2's report. Defaults to the target's name.",
    )
    parser.add_argument(
        "--artifacts",
        default=str(contracts.DEFAULT_ARTIFACT_DIR),
        help="Directory for the stage artifacts (default: ./artifacts).",
    )
    parser.add_argument(
        "--only",
        choices=["1", "2"],
        default=None,
        help="Run a single stage against the artifacts already on disk.",
    )
    parser.add_argument(
        "--no-git",
        action="store_true",
        help="Skip git history mining. Faster, but leaves commit_frequency, "
             "author_count, bug_history and days_since_last_change at defaults.",
    )
    parser.add_argument("--c1-python", default=None, help="Interpreter for C1.")
    parser.add_argument("--c2-python", default=None, help="Interpreter for C2.")
    return parser.parse_args(argv)


def _banner(text: str) -> None:
    # Flushed so the banner can't land after a subprocess's stderr and make a
    # failure look like it came from the wrong stage.
    print(f"\n{'=' * 62}\n  {text}\n{'=' * 62}", flush=True)


def main(argv=None) -> int:
    args = parse_args(argv)

    artifact_dir = Path(args.artifacts).resolve()
    project_name = args.project_name or Path(args.target).resolve().name

    run_stage1 = args.only in (None, "1")
    run_stage2 = args.only in (None, "2")

    if run_stage1:
        _banner("Stage 1 -- C1 static analysis + C1->C2 adapter")
        try:
            summary = stage1_static_analysis.run(
                target=args.target,
                artifact_dir=artifact_dir,
                project_name=project_name,
                python_exe=args.c1_python,
                mine_git=not args.no_git,
            )
        except stage1_static_analysis.Stage1Error as error:
            print(f"\n  Stage 1 failed: {error}", file=sys.stderr)
            return 1

        print(f"  files analysed      : {summary['files_analyzed']}")
        print(f"  functions extracted : {summary['functions_extracted']}")

        git = summary.get("git", {})
        if not git.get("enabled"):
            print("  git history         : skipped (--no-git)")
        elif not git.get("repo_root"):
            print("  git history         : unavailable — target is not in a git repo")
        else:
            print(
                f"  git history         : {git.get('mined', 0)} mined, "
                f"{git.get('defaulted', 0)} defaulted, "
                f"{git.get('cache_hits', 0)} cached"
            )

        spec = summary.get("spec", {})
        if spec:
            print(
                f"  documented funcs    : {spec.get('documented', 0)}"
                f" / {spec.get('functions', 0)}"
                f"  (README requirements: {spec.get('readme_requirements', 0)})"
            )

        print(f"  -> {summary['raw_artifact']}")
        print(f"  -> {summary['c2_input_artifact']}")
        if summary.get("spec_artifact"):
            print(f"  -> {summary['spec_artifact']}")

        skipped = summary.get("async_functions_skipped") or []
        if skipped:
            shown = ", ".join(skipped[:5])
            more = f" (+{len(skipped) - 5} more)" if len(skipped) > 5 else ""
            print(
                f"\n  NOTE: {len(skipped)} async function(s) skipped -- C1's "
                f"calculators only visit ast.FunctionDef.\n"
                f"        {shown}{more}"
            )

    if run_stage2:
        _banner("Stage 2 -- C2 ML risk scoring")
        try:
            result = stage2_ml_risk.run(
                artifact_dir=artifact_dir,
                python_exe=args.c2_python,
            )
        except stage2_ml_risk.Stage2Error as error:
            print(f"\n  Stage 2 failed: {error}", file=sys.stderr)
            return 1

        print(f"  -> {result['ml_output_artifact']}")

        ml_output = json.loads(
            Path(result["ml_output_artifact"]).read_text(encoding="utf-8")
        )
        summary = ml_output.get("summary", {})
        print(
            f"  HIGH={summary.get('high_risk_count')} "
            f"MEDIUM={summary.get('medium_risk_count')} "
            f"LOW={summary.get('low_risk_count')}  "
            f"avg={summary.get('average_risk_score')}"
        )

    _banner("Done")
    print(
        "  Stage 3 (C3 LLM test generation) is not wired in yet.\n"
        f"  It consumes {artifact_dir / contracts.STAGE2_ML_OUTPUT}, which is\n"
        "  already in the format src/utils/ml_report_reader.py expects."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
