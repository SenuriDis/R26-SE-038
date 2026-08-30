"""
Pulls the pipeline's scattered artifacts into one readable report.

A run leaves seven JSON files across three directories. That is fine for
machines and useless for a person, so this collapses them into a single
Markdown document: what was analysed, what looked risky, what tests were
written, what they found.

Markdown because it is what GitHub renders natively -- the same text works as
a job summary, a pull request comment, or a file you can read on its own.

    python -m pipeline.report artifacts/ > report.md
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from pipeline import contracts

# C3's reviewer emits CRITICAL as well as the four obvious levels. Leaving it
# out sorted the most serious findings to the bottom of the report.
SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}


def _load(path: Path) -> Optional[Dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def _latest_c3_run(artifact_dir: Path) -> Optional[Path]:
    """C3 writes one directory per run; the newest is the one that matters."""
    root = artifact_dir / "c3_output"
    if not root.exists():
        return None

    runs = sorted(
        (p for p in root.iterdir() if p.is_dir() and p.name.startswith("run_")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return runs[0] if runs else None


def _risk_section(ml: Dict, limit: int = 10) -> List[str]:
    tiers = ml.get("tier_breakdown", {})
    summary = ml.get("summary", {})

    lines = [
        "## Risk ranking",
        "",
        f"- **{summary.get('total_functions', 0)}** functions analysed",
        f"- {tiers.get('HIGH', {}).get('functions', []).__len__()} high, "
        f"{tiers.get('MEDIUM', {}).get('functions', []).__len__()} medium, "
        f"{tiers.get('LOW', {}).get('functions', []).__len__()} low",
        "",
    ]

    ranked = [f for tier in tiers.values() for f in tier.get("functions", [])]
    ranked.sort(key=lambda f: f.get("risk_score", 0), reverse=True)

    if not ranked:
        lines.append("_No functions were ranked._")
        return lines

    lines += [
        "| Function | File | Risk | Tier | Why |",
        "|---|---|---|---|---|",
    ]
    for fn in ranked[:limit]:
        factors = fn.get("top_risk_factors") or []
        why = ", ".join(
            f["feature"].replace("_", " ") for f in factors[:2]
        ) or "—"
        lines.append(
            f"| `{fn['function_name']}` | `{fn['file_path']}` | "
            f"{fn.get('risk_score', 0):.3f} | {fn.get('risk_level', '?')} | {why} |"
        )

    if len(ranked) > limit:
        lines.append(f"\n_…and {len(ranked) - limit} more._")

    return lines


def _spec_section(spec: Dict) -> List[str]:
    """Documentation gaps -- promises the code does not keep."""
    functions = spec.get("functions", [])
    flagged = [
        f for f in functions
        if any(f.get("gap_analysis", {}).values())
    ]

    if not flagged:
        return []

    lines = [
        "## Documentation gaps",
        "",
        "Where the docstring and the code disagree.",
        "",
        "| Function | Gap |",
        "|---|---|",
    ]
    for f in flagged[:10]:
        gaps = [
            k.replace("missing_", "").replace("_", " ")
            for k, v in f["gap_analysis"].items() if v
        ]
        lines.append(f"| `{f['function_name']}` | {', '.join(gaps)} |")

    return lines


def _tests_section(run_dir: Path) -> List[str]:
    summary = _load(run_dir / "run_summary.json") or {}
    traceability = _load(run_dir / "traceability_report.json") or {}

    generated = sorted((run_dir / "generated_tests").glob("test_*.py"))

    lines = [
        "## Generated tests",
        "",
        f"- **{summary.get('segments_with_valid_tests', 0)}"
        f" / {summary.get('segments_processed', 0)}** functions produced valid tests",
        f"- {len(generated)} test file(s) written",
        "",
    ]

    segments = traceability.get("segments", [])
    if segments:
        lines += ["| Function | Test cases covered |", "|---|---|"]
        for seg in segments:
            trace = seg.get("traceability", {})
            lines.append(
                f"| `{seg.get('function_name')}` | "
                f"{trace.get('covered_count', 0)}/{trace.get('total_test_cases', 0)} |"
            )
        lines.append("")

    return lines


def _review_section(run_dir: Path, limit: int = 8) -> List[str]:
    review = _load(run_dir / "code_review_report.json")
    if not review:
        return []

    findings = []
    for report in review.get("reports", []):
        for finding in report.get("findings", []):
            findings.append((report.get("function_name"), finding))

    if not findings:
        return []

    findings.sort(key=lambda pair: SEVERITY_ORDER.get(
        str(pair[1].get("severity", "")).upper(), 9
    ))

    lines = [
        "## Code review",
        "",
        f"{len(findings)} finding(s) across "
        f"{len(review.get('reports', []))} function(s).",
        "",
    ]
    for function_name, finding in findings[:limit]:
        severity = str(finding.get("severity", "?")).upper()
        lines.append(
            f"- **{severity}** in `{function_name}` — "
            f"{finding.get('description', '').strip()}"
        )

    if len(findings) > limit:
        lines.append(f"- _…and {len(findings) - limit} more._")

    lines.append("")
    return lines


def _evaluation_section(evaluation: Dict) -> List[str]:
    tests = evaluation.get("test_results", {})
    coverage = evaluation.get("coverage_metrics", {})

    failed = tests.get("failed_tests", []) or []
    real_defects = [t for t in failed if t.get("failure_type") == "Real Defect"]

    lines = [
        "## Test execution",
        "",
        f"| | |",
        f"|---|---|",
        f"| Passed | {tests.get('passed', 0)} / {tests.get('total', 0)} |",
        f"| Statement coverage | {coverage.get('statement_coverage_pct', 0)}% |",
        f"| Branch coverage | {coverage.get('branch_coverage_pct', 0)}% |",
        "",
    ]

    if real_defects:
        lines += [
            f"### {len(real_defects)} likely defect(s) found",
            "",
        ]
        for test in real_defects[:5]:
            name = test.get("name", "").split("::")[-1]
            assertion = next(
                (l.strip() for l in str(test.get("message", "")).splitlines()
                 if l.strip().startswith("E ")),
                "",
            )
            lines.append(f"- `{name}`")
            if assertion:
                lines.append(f"  ```\n  {assertion.lstrip('E ').strip()}\n  ```")
        lines.append("")

    other = [t for t in failed if t.get("failure_type") != "Real Defect"]
    if other:
        kinds = {}
        for test in other:
            kinds[test.get("failure_type", "?")] = kinds.get(test.get("failure_type", "?"), 0) + 1
        detail = ", ".join(f"{count} {kind}" for kind, count in kinds.items())
        lines += [f"Other failures: {detail}.", ""]

    return lines


def build(artifact_dir: Path, title: str = "Automated test analysis") -> str:
    """Assemble the Markdown report from whatever artifacts exist."""
    artifact_dir = Path(artifact_dir)

    ml = _load(artifact_dir / contracts.STAGE2_ML_OUTPUT)
    spec = _load(artifact_dir / contracts.STAGE1_SPEC)
    c2_input = _load(artifact_dir / contracts.STAGE1_C2_INPUT)
    run_dir = _latest_c3_run(artifact_dir)
    evaluation = _load(artifact_dir / "c4_workdir" / "reports" / "evaluation_report.json")

    lines = [f"# {title}", ""]

    if c2_input:
        project = c2_input.get("project_name", "project")
        lines.append(f"**Project:** `{project}`  ")
        lines.append(f"**Functions analysed:** {len(c2_input.get('functions', []))}")
        lines.append("")

    if not any([ml, spec, run_dir, evaluation]):
        lines.append("_No pipeline artifacts found._")
        return "\n".join(lines)

    # Headline first: what did it actually find?
    if evaluation:
        failed = evaluation.get("test_results", {}).get("failed_tests", []) or []
        defects = [t for t in failed if t.get("failure_type") == "Real Defect"]
        if defects:
            lines += [
                f"> **{len(defects)} likely defect(s) found** by generated tests.",
                "",
            ]

    if ml:
        lines += _risk_section(ml) + [""]
    if spec:
        lines += _spec_section(spec) + [""]
    if run_dir:
        lines += _tests_section(run_dir)
        lines += _review_section(run_dir)
    if evaluation:
        lines += _evaluation_section(evaluation)

    lines += [
        "---",
        "",
        "<sub>Generated by R26-SE-038 — static analysis, ML risk ranking, "
        "LLM test generation, and test execution.</sub>",
    ]

    return "\n".join(lines)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build a Markdown report from pipeline artifacts.")
    parser.add_argument("artifact_dir", nargs="?", default=str(contracts.DEFAULT_ARTIFACT_DIR))
    parser.add_argument("--title", default="Automated test analysis")
    parser.add_argument("-o", "--output", default=None, help="Write to a file instead of stdout.")
    args = parser.parse_args()

    text = build(Path(args.artifact_dir), args.title)

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"wrote {args.output}")
        return 0

    # LLM-written descriptions carry characters cp1252 cannot encode -- a
    # non-breaking hyphen is enough to crash printing on a default Windows
    # console. Write UTF-8 bytes directly rather than relying on the console
    # codec.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        print(text)
    except (AttributeError, OSError):
        sys.stdout.buffer.write(text.encode("utf-8", errors="replace") + b"\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
