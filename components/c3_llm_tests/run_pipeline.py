"""
run_pipeline.py
────────────────
Main CLI entry point for Component 3.

Usage:
    python run_pipeline.py \
        --repo-path /path/to/repository \
        --ml-report ml_output.json \
        --output-dir ./results \
        --min-risk-level MEDIUM

Arguments:
    --repo-path      : Path to the repository to test
    --ml-report      : Path to Component 2's JSON output
    --output-dir     : Where to save results (default: ./outputs)
    --min-risk-level : Minimum risk tier to process (HIGH/MEDIUM/LOW)
    --force-reindex  : Force rebuild of ChromaDB index

Examples:
    # Process only HIGH risk functions
    python run_pipeline.py \
        --repo-path D:/projects/payment-service \
        --ml-report ml_output.json \
        --min-risk-level HIGH

    # Process HIGH and MEDIUM risk functions (default)
    python run_pipeline.py \
        --repo-path D:/projects/payment-service \
        --ml-report ml_output.json

    # Process all functions including LOW risk
    python run_pipeline.py \
        --repo-path D:/projects/payment-service \
        --ml-report ml_output.json \
        --min-risk-level LOW
"""

import argparse
import logging
import sys
import uuid
from pathlib import Path

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="R26-SE-038 — LLM Test Generation & Code Review Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--repo-path",
        required=True,
        help="Absolute path to the repository to test",
    )
    parser.add_argument(
        "--ml-report",
        required=True,
        help="Path to Component 2's ML risk report JSON file",
    )
    parser.add_argument(
        "--output-dir",
        default="./outputs",
        help="Directory to save results (default: ./outputs)",
    )
    parser.add_argument(
        "--min-risk-level",
        choices=["HIGH", "MEDIUM", "LOW"],
        default="MEDIUM",
        help="Minimum risk tier to process (default: MEDIUM)",
    )
    parser.add_argument(
        "--force-reindex",
        action="store_true",
        help="Force rebuild of ChromaDB vector index",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Custom run ID (default: auto-generated)",
    )

    return parser.parse_args()


def print_banner():
    print()
    print("=" * 65)
    print("  R26-SE-038 | Intelligent Software Testing System")
    print("  LLM-Based Test Generation & Code Review — Component 3")
    print("=" * 65)
    print()


def print_summary(output, written_files):
    print()
    print("=" * 65)
    print("  PIPELINE RESULTS")
    print("=" * 65)
    print()
    print(f"  Run ID              : {output.run_id}")
    print(f"  Segments Processed  : {output.segments_processed}")
    print(f"  Valid Tests         : {output.segments_with_valid_tests}")
    print(f"  Success Rate        : {output.success_rate * 100:.1f}%")
    print()

    # Per-function summary
    print("  FUNCTION RESULTS")
    print("  " + "-" * 50)
    for test in output.validated_tests:
        status = "✅" if test.is_syntactically_valid else "❌"
        repairs = f"({test.total_repairs} repairs)" if test.total_repairs > 0 else ""
        trace = ""
        if test.traceability_report:
            tr = test.traceability_report
            trace = f"| trace {tr.covered_count}/{tr.total_test_cases}"
        print(
            f"  {status} {test.function_name}() "
            f"{repairs} {trace}"
        )

    print()
    print("  CODE REVIEW FINDINGS")
    print("  " + "-" * 50)
    for review in output.code_review_reports:
        pylint = f"pylint={review.pylint_score}/10" if review.pylint_score else ""
        print(f"  🔍 {review.function_name}() | {pylint} | {review.total_findings} findings")
        for finding in review.findings:
            sev = finding.severity.value.upper()
            print(f"     [{sev}] {finding.description}")

    if output.errors:
        print()
        print("  ERRORS")
        print("  " + "-" * 50)
        for error in output.errors:
            print(f"  ⚠ {error}")

    print()
    print("  OUTPUT FILES")
    print("  " + "-" * 50)
    for test_file in written_files.get("test_files", []):
        print(f"  📄 {test_file}")
    if written_files.get("review_report"):
        print(f"  📋 {written_files['review_report']}")
    if written_files.get("traceability_report"):
        print(f"  📊 {written_files['traceability_report']}")
    if written_files.get("summary"):
        print(f"  📝 {written_files['summary']}")
    print()


def main():
    print_banner()
    args = parse_args()

    # ── Validate inputs ────────────────────────────────────────────────────
    repo_path = Path(args.repo_path).resolve()
    ml_report_path = Path(args.ml_report).resolve()
    output_dir = args.output_dir
    run_id = args.run_id or str(uuid.uuid4())[:8]

    if not repo_path.exists():
        logger.error(f"Repository not found: {repo_path}")
        sys.exit(1)

    if not ml_report_path.exists():
        logger.error(f"ML report not found: {ml_report_path}")
        sys.exit(1)

    print(f"  Repository   : {repo_path}")
    print(f"  ML Report    : {ml_report_path}")
    print(f"  Output Dir   : {output_dir}")
    print(f"  Min Risk     : {args.min_risk_level}")
    print(f"  Run ID       : {run_id}")
    print()

    # ── Import pipeline components ─────────────────────────────────────────
    from src.utils.ml_report_reader import MLReportReader
    from src.pipeline.pipeline import TestingPipeline
    from src.utils.output_writer import OutputWriter

    # ── Step 1: Read ML report ─────────────────────────────────────────────
    logger.info("Reading ML report...")
    try:
        reader = MLReportReader(
            report_path=str(ml_report_path),
            repository_path=str(repo_path),
        )
        enriched_segments = reader.load(min_risk_level=args.min_risk_level)
        summary = reader.get_summary()

        print(f"  ML Report Summary:")
        print(f"    Total functions    : {summary.get('total_functions', '?')}")
        print(f"    High risk          : {summary.get('high_risk_count', '?')}")
        print(f"    Medium risk        : {summary.get('medium_risk_count', '?')}")
        print(f"    Low risk           : {summary.get('low_risk_count', '?')}")
        print(f"    Processing         : {len(enriched_segments)} functions")
        print()

    except Exception as e:
        logger.error(f"Failed to read ML report: {e}")
        sys.exit(1)

    if not enriched_segments:
        logger.warning(
            f"No functions found at or above {args.min_risk_level} risk level. "
            f"Try --min-risk-level LOW to include all functions."
        )
        sys.exit(0)

    # ── Step 2: Run pipeline ───────────────────────────────────────────────
    logger.info(f"Starting pipeline with {len(enriched_segments)} segments...")
    try:
        pipeline = TestingPipeline(force_reindex=args.force_reindex)
        output = pipeline.run_from_ml_report(
            repository_path=str(repo_path),
            enriched_segments=enriched_segments,
            run_id=run_id,
        )
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)

    # ── Step 3: Save outputs ───────────────────────────────────────────────
    logger.info("Saving outputs...")
    try:
        writer = OutputWriter(output_dir=output_dir)
        written_files = writer.save(output)
    except Exception as e:
        logger.error(f"Failed to save outputs: {e}")
        sys.exit(1)

    # ── Step 4: Print summary ──────────────────────────────────────────────
    print_summary(output, written_files)

    # ── Exit code ──────────────────────────────────────────────────────────
    # Exit 1 if any critical bugs found or tests failed
    # This allows CI/CD to block merges on critical findings
    critical_findings = []
    for review in output.code_review_reports:
        for finding in review.findings:
            if finding.severity.value in ["critical", "high"]:
                critical_findings.append(finding)

    if critical_findings:
        logger.warning(
            f"Found {len(critical_findings)} critical/high severity findings. "
            f"Review recommended before merging."
        )

    if output.success_rate < 0.8:
        logger.warning(
            f"Test validity rate {output.success_rate:.1%} is below 80% target."
        )

    sys.exit(0)


if __name__ == "__main__":
    main()