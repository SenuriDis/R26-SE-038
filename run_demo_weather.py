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
    print("  WEATHER-01 | Weather Utilities Testing Demo")
    print("="*60 + "\n")

    segments = [
        HighRiskSegment(
            segment_id="weather-001",
            file_path="sample_project/weather_utils.py",
            function_name="celsius_to_fahrenheit",
            source_code="""def celsius_to_fahrenheit(celsius):
    return (celsius * 9/5) + 32""",
            risk_score=0.70,
            start_line=1,
            end_line=2,
            cyclomatic_complexity=1,
        ),
        HighRiskSegment(
            segment_id="weather-002",
            file_path="sample_project/weather_utils.py",
            function_name="heat_index",
            source_code="""def heat_index(temp_celsius, humidity):
    if temp_celsius < 27:
        return temp_celsius
    
    hi = temp_celsius + (humidity / 100) * 0.5
    return round(hi, 1)""",
            risk_score=0.85,
            start_line=10,
            end_line=16,
            cyclomatic_complexity=2,
        ),
        HighRiskSegment(
            segment_id="weather-003",
            file_path="sample_project/weather_utils.py",
            function_name="wind_chill",
            source_code="""def wind_chill(temp_celsius, wind_speed_kmh):
    if temp_celsius > 10 or wind_speed_kmh < 4.8:
        return temp_celsius
    
    wc = 13.12 + 0.6215 * temp_celsius - 11.37 * (wind_speed_kmh ** 0.16) + 0.3965 * temp_celsius * (wind_speed_kmh ** 0.16)
    return round(wc, 1)""",
            risk_score=0.92,
            start_line=18,
            end_line=24,
            cyclomatic_complexity=3,
        ),
        HighRiskSegment(
            segment_id="weather-004",
            file_path="sample_project/weather_utils.py",
            function_name="calculate_uv_index",
            source_code="""def calculate_uv_index(ozone, angle, cloud_cover):
    base_uv = ozone / 300 * 10
    
    if angle > 90:
        angle = 90
    
    angle_factor = angle / 90
    uv = base_uv * angle_factor
    
    cloud_factor = 1 - (cloud_cover / 100) * 0.5
    uv = uv * cloud_factor
    
    return round(max(0, uv), 1)""",
            risk_score=0.88,
            start_line=26,
            end_line=38,
            cyclomatic_complexity=3,
        ),
    ]

    pipeline_input = PipelineInput(
        repository_path=str(Path(__file__).parent / "sample_project"),
        segments=segments,
        run_id="weather-demo-001",
    )

    pipeline = TestingPipeline()
    output = pipeline.run(pipeline_input)

    print("\n" + "="*60)
    print("  WEATHER UTILITIES RESULTS")
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