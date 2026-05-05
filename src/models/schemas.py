from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ── Enums 

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
    INFO     = "info"


class ReviewCategory(str, Enum):
    CODE_SMELL      = "code_smell"
    SOLID_VIOLATION = "solid_violation"
    MAINTAINABILITY = "maintainability"
    BUG             = "bug"
    SECURITY        = "security"


class RepairStatus(str, Enum):
    NOT_ATTEMPTED  = "not_attempted"
    SUCCESS        = "success"
    FAILED         = "failed"
    MAX_ITERATIONS = "max_iterations_reached"


# ── Input from Component 2 

class HighRiskSegment(BaseModel):
    segment_id: str
    file_path: str
    function_name: str
    source_code: str
    risk_score: float = Field(..., ge=0.0, le=1.0)
    start_line: int
    end_line: int
    cyclomatic_complexity: Optional[int] = None
    language: str = "python"


class PipelineInput(BaseModel):
    repository_path: str
    segments: list[HighRiskSegment]
    run_id: str


# ── Agent 1 Output 

class RawTestOutput(BaseModel):
    segment_id: str
    function_name: str
    file_path: str
    raw_test_code: str
    rag_context_used: bool = False
    prompt_tokens: int = 0
    completion_tokens: int = 0


# ── Agent 2 Output 

class RepairIteration(BaseModel):
    iteration: int
    error_type: str
    error_message: str
    repair_applied: bool


class ValidatedTestOutput(BaseModel):
    segment_id: str
    function_name: str
    file_path: str
    validated_test_code: str
    is_syntactically_valid: bool
    repair_status: RepairStatus = RepairStatus.NOT_ATTEMPTED
    repair_iterations: list[RepairIteration] = []
    total_repairs: int = 0
    output_file_path: Optional[str] = None


# ── Agent 3 Output 

class ReviewFinding(BaseModel):
    finding_id: str
    category: ReviewCategory
    severity: Severity
    line_number: Optional[int] = None
    description: str
    suggested_fix: str


class CodeReviewReport(BaseModel):
    segment_id: str
    function_name: str
    file_path: str
    findings: list[ReviewFinding] = []
    total_findings: int = 0
    pylint_score: Optional[float] = None
    summary: str
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def model_post_init(self, __context):
        self.total_findings = len(self.findings)


# ── Final Output to Component 4 

class PipelineOutput(BaseModel):
    run_id: str
    repository_path: str
    segments_processed: int
    segments_with_valid_tests: int
    validated_tests: list[ValidatedTestOutput] = []
    code_review_reports: list[CodeReviewReport] = []
    success_rate: float = 0.0
    errors: list[str] = []

    def model_post_init(self, __context):
        if self.segments_processed > 0:
            self.success_rate = round(
                self.segments_with_valid_tests / self.segments_processed, 4
            )