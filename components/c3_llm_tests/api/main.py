import logging
import uuid
import tempfile
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional

from src.models.schemas import HighRiskSegment, PipelineInput
from src.pipeline.pipeline import TestingPipeline
from src.utils.ml_report_reader import enrich_segment
from src.utils.output_writer import OutputWriter
from api.wizard_source import write_source_files

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="R26-SE-038 | LLM Testing Pipeline API",
    description="Automated test generation and code review using LLMs",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Models ─────────────────────────────────────────────────────────────

class SegmentRequest(BaseModel):
    function_name: str
    file_path: str
    source_code: str
    risk_score: float = 0.85
    cyclomatic_complexity: Optional[int] = None  # C2's ranked output does not carry it
    # Component 2's guidance for this function. When risk_level is sent,
    # Agent 1 is driven exactly as in the CLI / GitHub Action path.
    risk_level: Optional[str] = None
    recommended_test_depth: Optional[str] = None
    test_types: Optional[list[str]] = None
    explanation_text: str = ""
    top_risk_factors: list[dict] = []
    confidence: float = 1.0


class PipelineRequest(BaseModel):
    repository_path: str
    segments: list[SegmentRequest]
    source_files: Optional[Dict[str, str]] = None


# ── Response Models ────────────────────────────────────────────────────────────

class TestCaseResponse(BaseModel):
    test_case_id: str
    description: str
    input_values: str
    expected_output: str
    category: str


class TraceabilityEntryResponse(BaseModel):
    test_case_id: str
    description: str
    implemented_by: Optional[str]
    is_covered: bool
    notes: Optional[str]


class TraceabilityResponse(BaseModel):
    total_test_cases: int
    covered_count: int
    coverage_rate: float
    entries: list[TraceabilityEntryResponse]


class RepairIterationResponse(BaseModel):
    iteration: int
    error_type: str
    error_message: str
    repair_applied: bool


class TestResult(BaseModel):
    function_name: str
    is_valid: bool
    repairs: int
    repair_status: str = "not_attempted"
    repair_iterations: list[RepairIterationResponse] = []
    test_code: str
    test_cases: list[TestCaseResponse] = []
    traceability: Optional[TraceabilityResponse] = None


class FindingResponse(BaseModel):
    finding_id: str
    category: str
    severity: str
    line_number: Optional[int]
    description: str
    suggested_fix: str


class ReviewResult(BaseModel):
    function_name: str
    pylint_score: Optional[float]
    summary: str
    findings: list[FindingResponse]


class PipelineResponse(BaseModel):
    run_id: str
    success_rate: float
    segments_processed: int
    segments_with_valid_tests: int
    tests: list[TestResult]
    reviews: list[ReviewResult]
    errors: list[str]


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "running", "project": "R26-SE-038", "version": "2.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/run", response_model=PipelineResponse)
def run_pipeline(request: PipelineRequest):
    try:
        if request.source_files is None:
            return _execute_pipeline(request, request.repository_path)

        data_root = Path("./data/wizard_sources").resolve()
        data_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="run-", dir=data_root) as source_root:
            write_source_files(Path(source_root), request.source_files)
            return _execute_pipeline(request, source_root)

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _execute_pipeline(request: PipelineRequest, repository_path: str) -> PipelineResponse:
    run_id = str(uuid.uuid4())[:8]
    segments = [
        HighRiskSegment(
            segment_id=f"seg-{i+1:03d}",
            file_path=seg.file_path,
            function_name=seg.function_name,
            source_code=seg.source_code,
            risk_score=seg.risk_score,
            start_line=1,
            end_line=len(seg.source_code.splitlines()),
            cyclomatic_complexity=seg.cyclomatic_complexity,
        )
        for i, seg in enumerate(request.segments)
    ]

    pipeline = TestingPipeline()
    if all(seg.risk_level for seg in request.segments):
        enriched = [
            enrich_segment(
                segment,
                risk_level=seg.risk_level,
                recommended_depth=seg.recommended_test_depth,
                recommended_types=seg.test_types,
                explanation_text=seg.explanation_text,
                top_risk_factors=seg.top_risk_factors,
                confidence=seg.confidence,
            )
            for segment, seg in zip(segments, request.segments)
        ]
        output = pipeline.run_from_ml_report(repository_path, enriched, run_id)
    else:
        output = pipeline.run(PipelineInput(
            repository_path=repository_path,
            segments=segments,
            run_id=run_id,
        ))

    writer = OutputWriter()
    writer.save(output)

    tests = []
    for test in output.validated_tests:
        traceability = None
        if test.traceability_report:
            report = test.traceability_report
            traceability = TraceabilityResponse(
                total_test_cases=report.total_test_cases,
                covered_count=report.covered_count,
                coverage_rate=report.coverage_rate,
                entries=[
                    TraceabilityEntryResponse(
                        test_case_id=entry.test_case_id,
                        description=entry.description,
                        implemented_by=entry.implemented_by,
                        is_covered=entry.is_covered,
                        notes=entry.notes,
                    )
                    for entry in report.entries
                ],
            )
        tests.append(TestResult(
            function_name=test.function_name,
            is_valid=test.is_syntactically_valid,
            repairs=test.total_repairs,
            repair_status=test.repair_status.value,
            repair_iterations=[
                RepairIterationResponse(**iteration.model_dump())
                for iteration in test.repair_iterations
            ],
            test_code=test.validated_test_code,
            test_cases=[
                TestCaseResponse(
                    test_case_id=case.test_case_id,
                    description=case.description,
                    input_values=case.input_values,
                    expected_output=case.expected_output,
                    category=case.category.value,
                )
                for case in test.test_case_set.test_cases
            ] if test.test_case_set else [],
            traceability=traceability,
        ))

    reviews = [
        ReviewResult(
            function_name=review.function_name,
            pylint_score=review.pylint_score,
            summary=review.summary,
            findings=[
                FindingResponse(
                    finding_id=finding.finding_id,
                    category=finding.category.value,
                    severity=finding.severity.value,
                    line_number=finding.line_number,
                    description=finding.description,
                    suggested_fix=finding.suggested_fix,
                )
                for finding in review.findings
            ],
        )
        for review in output.code_review_reports
    ]
    return PipelineResponse(
        run_id=run_id,
        success_rate=output.success_rate,
        segments_processed=output.segments_processed,
        segments_with_valid_tests=output.segments_with_valid_tests,
        tests=tests,
        reviews=reviews,
        errors=output.errors,
    )