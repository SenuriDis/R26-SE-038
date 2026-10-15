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
    print("  R26-SE-038 | Real Repo Demo - requests library")
    print("="*60 + "\n")

    # Real functions from the requests library
    # These are what Component 2 would send us after ML risk scoring
    segments = [
        HighRiskSegment(
            segment_id="req-001",
            file_path="src/requests/utils.py",
            function_name="check_header_validity",
            source_code="""def check_header_validity(header):
    name, value = header

    for pat in (CLEAN_HEADER_REGEX_BYTE, CLEAN_HEADER_REGEX_STR):
        try:
            if pat.search(name):
                raise InvalidHeader(
                    f"Invalid leading whitespace, reserved char in header name: {name!r}"
                )
            if pat.search(value):
                raise InvalidHeader(
                    f"Invalid leading whitespace, reserved char in header value: {value!r}"
                )
        except TypeError:
            pass""",
            risk_score=0.88,
            start_line=1,
            end_line=14,
            cyclomatic_complexity=4,
        ),
        HighRiskSegment(
            segment_id="req-002",
            file_path="src/requests/utils.py",
            function_name="get_encoding_from_headers",
            source_code="""def get_encoding_from_headers(headers):
    content_type = headers.get("content-type")

    if not content_type:
        return None

    encoding = requests.utils.parse_header(content_type).get("charset")

    if encoding:
        encoding = encoding.strip("'\"")

    if encoding and codecs.lookup(encoding):
        return encoding

    return None""",
            risk_score=0.82,
            start_line=1,
            end_line=14,
            cyclomatic_complexity=5,
        ),
        HighRiskSegment(
            segment_id="req-003",
            file_path="src/requests/utils.py",
            function_name="prepend_scheme_if_needed",
            source_code="""def prepend_scheme_if_needed(url, new_scheme):
    parsed = parse_url(url)
    scheme, auth, host, port, path, query, fragment = parsed

    if not scheme:
        scheme = new_scheme

    if not host:
        netloc = path
        path = ""
    elif auth:
        netloc = "@".join([auth, host])
    else:
        netloc = host

    if port:
        netloc = ":".join([netloc, str(port)])

    return urlunparse((scheme, netloc, path, "", query or "", fragment or ""))""",
            risk_score=0.79,
            start_line=1,
            end_line=18,
            cyclomatic_complexity=6,
        ),
    ]

    # Point the pipeline at the real requests repo
    #requests_repo_path = str(
    #    Path(__file__).parent / "temp_repos" / "requests" / "src" / "requests"
    #)

    requests_repo_path = r"D:\Year 4 Sem 1\temp_repos\requests\src\requests"

    pipeline_input = PipelineInput(
        repository_path=requests_repo_path,
        segments=segments,
        run_id="requests-demo-001",
    )

    # Run the pipeline
    pipeline = TestingPipeline()
    output = pipeline.run(pipeline_input)

    # Save outputs
    writer = OutputWriter(output_dir="./outputs")
    written_files = writer.save(output)

    # Print results
    print("\n" + "="*60)
    print("  RESULTS")
    print("="*60)

    print(f"\n✅ Segments processed  : {output.segments_processed}")
    print(f"✅ Valid tests generated: {output.segments_with_valid_tests}")
    print(f"✅ Success rate         : {output.success_rate * 100:.1f}%")

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

    print("\n--- OUTPUT FILES ---\n")
    for test_file in written_files["test_files"]:
        print(f"  📄 {test_file}")
    print(f"  📋 {written_files['review_report']}")
    print(f"  📊 {written_files['summary']}")

    if output.errors:
        print("\n--- ERRORS ---")
        for e in output.errors:
            print(f"  ⚠ {e}")


if __name__ == "__main__":
    main()