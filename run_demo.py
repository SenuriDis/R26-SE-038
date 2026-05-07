import logging
import sys
from pathlib import Path

# Make sure Python can find our modules
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(message)s"
)

from src.models.schemas import HighRiskSegment, PipelineInput
from src.pipeline.pipeline import TestingPipeline


def main():
    print("\n" + "="*60)
    print("  R26-SE-038 | LLM Testing Pipeline Demo")
    print("="*60 + "\n")

    # Simulate what Component 2 (ML team) would send us
    # These are the "high risk" segments they identified
    segments = [
        HighRiskSegment(
            segment_id="seg-001",
            file_path="sample_project/calculator.py",
            function_name="divide",
            source_code="""def divide(a, b):
    return a / b""",
            risk_score=0.91,
            start_line=5,
            end_line=6,
            cyclomatic_complexity=1,
        ),
        HighRiskSegment(
            segment_id="seg-002",
            file_path="sample_project/calculator.py",
            function_name="calculate_average",
            source_code="""def calculate_average(numbers):
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)""",
            risk_score=0.85,
            start_line=21,
            end_line=25,
            cyclomatic_complexity=2,
        ),
    ]

    pipeline_input = PipelineInput(
        repository_path=str(Path(__file__).parent / "sample_project"),
        segments=segments,
        run_id="demo-run-001",
    )

    # Run the pipeline
    pipeline = TestingPipeline()
    output = pipeline.run(pipeline_input)

    # Print results
    print("\n" + "="*60)
    print("  RESULTS")
    print("="*60)

    print(f"\n✅ Segments processed : {output.segments_processed}")
    print(f"✅ Valid tests generated: {output.segments_with_valid_tests}")
    print(f"✅ Success rate        : {output.success_rate * 100:.1f}%")

    print("\n--- GENERATED TESTS ---\n")
    for test in output.validated_tests:
        print(f"Function : {test.function_name}")
        print(f"Valid    : {test.is_syntactically_valid}")
        print(f"Repairs  : {test.total_repairs}")
        print(f"Code:\n{test.validated_test_code}")
        print("-" * 40)

    print("\n--- CODE REVIEW REPORTS ---\n")
    for report in output.code_review_reports:
        print(f"Function : {report.function_name}")
        print(f"Pylint   : {report.pylint_score}")
        print(f"Summary  : {report.summary}")
        print(f"Findings : {report.total_findings}")
        for f in report.findings:
            print(f"  [{f.severity.value.upper()}] {f.category.value} — {f.description}")
        print("-" * 40)

    if output.errors:
        print("\n--- ERRORS ---")
        for e in output.errors:
            print(f"  ⚠ {e}")


if __name__ == "__main__":
    main()