import logging
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.models.schemas import HighRiskSegment, PipelineInput
from src.pipeline.pipeline import TestingPipeline
from src.utils.output_writer import OutputWriter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="R26-SE-038 | LLM Testing Pipeline API",
    description="Automated test generation and code review using LLMs",
    version="1.0.0",
)

# Allow frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/Response models ───────────────────────────────────────────────────

class SegmentRequest(BaseModel):
    function_name: str
    file_path: str
    source_code: str
    risk_score: float = 0.85
    cyclomatic_complexity: int = 3


class PipelineRequest(BaseModel):
    repository_path: str
    segments: list[SegmentRequest]


class FindingResponse(BaseModel):
    finding_id: str
    category: str
    severity: str
    line_number: int | None
    description: str
    suggested_fix: str


class TestResult(BaseModel):
    function_name: str
    is_valid: bool
    repairs: int
    test_code: str


class ReviewResult(BaseModel):
    function_name: str
    pylint_score: float | None
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


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "running", "project": "R26-SE-038"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/run", response_model=PipelineResponse)
def run_pipeline(request: PipelineRequest):
    """
    Run the full three-agent pipeline on the given code segments.
    This is the main endpoint the frontend calls.
    """
    try:
        run_id = str(uuid.uuid4())[:8]

        # Build segments
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

        # Run pipeline
        pipeline = TestingPipeline()
        output = pipeline.run(pipeline_input)

        # Save outputs to disk
        writer = OutputWriter()
        writer.save(output)

        # Build response
        tests = [
            TestResult(
                function_name=t.function_name,
                is_valid=t.is_syntactically_valid,
                repairs=t.total_repairs,
                test_code=t.validated_test_code,
            )
            for t in output.validated_tests
        ]

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