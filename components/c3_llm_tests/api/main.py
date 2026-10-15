import logging
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from src.models.schemas import HighRiskSegment, PipelineInput
from src.pipeline.pipeline import TestingPipeline
from src.utils.output_writer import OutputWriter

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
    cyclomatic_complexity: int = 3


class PipelineRequest(BaseModel):
    repository_path: str
    segments: list[SegmentRequest]


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


class TestResult(BaseModel):
    function_name: str
    is_valid: bool
    repairs: int
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

        pipeline_input = PipelineInput(
            repository_path=request.repository_path,
            segments=segments,
            run_id=run_id,
        )

        pipeline = TestingPipeline()
        output = pipeline.run(pipeline_input)

        writer = OutputWriter()
        writer.save(output)

        # Build test results with test cases and traceability
        tests = []
        for t in output.validated_tests:
            test_cases = []
            if t.traceability_report and hasattr(t, 'traceability_report'):
                # Get test cases from the raw output via pipeline
                pass

            traceability = None
            if t.traceability_report:
                tr = t.traceability_report
                traceability = TraceabilityResponse(
                    total_test_cases=tr.total_test_cases,
                    covered_count=tr.covered_count,
                    coverage_rate=tr.coverage_rate,
                    entries=[
                        TraceabilityEntryResponse(
                            test_case_id=e.test_case_id,
                            description=e.description,
                            implemented_by=e.implemented_by,
                            is_covered=e.is_covered,
                            notes=e.notes,
                        )
                        for e in tr.entries
                    ],
                )

            tests.append(TestResult(
                function_name=t.function_name,
                is_valid=t.is_syntactically_valid,
                repairs=t.total_repairs,
                test_code=t.validated_test_code,
                test_cases=test_cases,
                traceability=traceability,
            ))

        reviews = [
            ReviewResult(
                function_name=r.function_name,
                pylint_score=r.pylint_score,
                summary=r.summary,
                findings=[
                    FindingResponse(
                        finding_id=f.finding_id,
                        category=f.category.value,
                        severity=f.severity.value,
                        line_number=f.line_number,
                        description=f.description,
                        suggested_fix=f.suggested_fix,
                    )
                    for f in r.findings
                ],
            )
            for r in output.code_review_reports
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

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))