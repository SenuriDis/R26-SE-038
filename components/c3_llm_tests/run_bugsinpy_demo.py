import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(message)s"
)

from src.models.schemas import HighRiskSegment, PipelineInput
from src.pipeline.pipeline import TestingPipeline
from src.utils.output_writer import OutputWriter


def main():
    print("\n" + "="*60)
    print("  BugsInPy Evaluation — thefuck bug #1")
    print("="*60)
    print()
    print("BUG DESCRIPTION:")
    print("  Regex pattern [a-z]+ only matches lowercase letters.")
    print("  Commands with uppercase, numbers or hyphens cause")
    print("  IndexError because findall returns empty list.")
    print()
    print("BUGGY CODE:")
    print("  re.findall(r'ERROR: unknown command \\\"([a-z]+)\\\"')")
    print()
    print("FIXED CODE:")
    print("  re.findall(r'ERROR: unknown command \"([^\"]+)\"')")
    print()

    # This is the BUGGY version — what we give to the pipeline
    buggy_source = '''import re

def get_new_command(command):
    broken_cmd = re.findall(
        r\'ERROR: unknown command \\"([a-z]+)\\"\',
        command.output
    )[0]
    new_cmd = re.findall(
        r\'maybe you meant \\"([a-z]+)\\"\',
        command.output
    )[0]
    return replace_argument(command.script, broken_cmd, new_cmd)'''

    segments = [
        HighRiskSegment(
            segment_id="bugsinpy-thefuck-001",
            file_path="thefuck/rules/pip_unknown_command.py",
            function_name="get_new_command",
            source_code=buggy_source,
            risk_score=0.88,
            start_line=12,
            end_line=19,
            cyclomatic_complexity=1,
        ),
    ]

    pipeline_input = PipelineInput(
        repository_path=str(Path(__file__).parent / "sample_project"),
        segments=segments,
        run_id="bugsinpy-thefuck-001",
    )

    pipeline = TestingPipeline()
    output = pipeline.run(pipeline_input)

    writer = OutputWriter(output_dir="./outputs")
    written_files = writer.save(output)

    # Print results
    print("\n" + "="*60)
    print("  PIPELINE RESULTS")
    print("="*60)
    print(f"\n✅ Success rate: {output.success_rate * 100:.1f}%")
    print(f"✅ Valid tests : {output.segments_with_valid_tests}/1")

    print("\n--- GENERATED TESTS ---\n")
    for test in output.validated_tests:
        print(f"Function : {test.function_name}")
        print(f"Valid    : {test.is_syntactically_valid}")
        print(f"Repairs  : {test.total_repairs}")
        print(f"\n{test.validated_test_code}")
        print("-" * 50)

    print("\n--- CODE REVIEW ---\n")
    for report in output.code_review_reports:
        print(f"Function : {report.function_name}")
        print(f"Pylint   : {report.pylint_score}")
        print(f"Summary  : {report.summary}")
        print(f"\nFindings ({report.total_findings}):")
        for f in report.findings:
            print(f"  [{f.severity.value.upper()}] {f.category.value}")
            print(f"  → {f.description}")
            print(f"  💡 {f.suggested_fix}")
            print()

    print("\n--- KEY QUESTION ---")
    print("Did Agent 1 generate a test that catches the bug?")
    print("(Look for tests using uppercase, numbers or hyphens in commands)")
    print()
    print("Did Agent 3 identify the regex limitation?")
    print("(Look for findings about regex pattern or input validation)")
    print()
    print("--- OUTPUT FILES ---")
    for f in written_files["test_files"]:
        print(f"  📄 {f}")
    print(f"  📋 {written_files['review_report']}")


if __name__ == "__main__":
    main()