"""
Converts a mapping + gap analysis into the numeric specification metrics
your ML model and unified feature matrix will consume.

Coverage score design (worth reading before you present this):

  - If a function has no documentation mapping at all (either the code
    is missing, or the code exists but isn't documented), the score is
    0.0. There's no partial credit for "coverage" when there's no
    spec to be covered by.

  - If a function IS documented and implemented, the score is the
    fraction of *applicable* checks it satisfies -- input validation
    (only counted if the requirement actually specifies input
    constraints), exception handling (only if exceptions are
    documented), and output definition (only if an expected output is
    documented). A requirement that doesn't mention exceptions at all
    shouldn't be penalised for "missing" exception handling.

  - If none of the three categories are documented for an otherwise
    mapped function (an edge case -- a requirement with just a
    function_name and nothing else), the score defaults to 1.0: there
    is nothing documented to fail.

This is a deliberate, simple weighting (equal weight per applicable
category). If your supervisor wants input/exception/output weighted
differently, that's a one-line change in _coverage_score below.
"""

from dataclasses import dataclass

from .code_requirement_mapper import MappingResult, MappingStatus
from .gap_detector import GapAnalysis


@dataclass
class SpecificationMetrics:
    has_documentation_mapping: bool
    input_requirements_count: int
    output_requirements_count: int
    exception_requirements_count: int
    specification_coverage_score: float


class SpecificationMetricsCalculator:
    def calculate(self, mapping: MappingResult, gaps: GapAnalysis) -> SpecificationMetrics:
        requirement = mapping.requirement

        input_count = len(requirement.inputs) if requirement else 0
        output_count = 1 if (requirement and requirement.expected_output) else 0
        exception_count = len(requirement.exceptions) if requirement else 0

        return SpecificationMetrics(
            has_documentation_mapping=mapping.status == MappingStatus.DOCUMENTED_IMPLEMENTED,
            input_requirements_count=input_count,
            output_requirements_count=output_count,
            exception_requirements_count=exception_count,
            specification_coverage_score=self._coverage_score(
                mapping, gaps, input_count, output_count, exception_count
            ),
        )

    @staticmethod
    def _coverage_score(
        mapping: MappingResult,
        gaps: GapAnalysis,
        input_count: int,
        output_count: int,
        exception_count: int,
    ) -> float:
        if mapping.status != MappingStatus.DOCUMENTED_IMPLEMENTED:
            return 0.0

        applicable_checks = []
        if input_count > 0:
            applicable_checks.append(not gaps.missing_input_validation)
        if exception_count > 0:
            applicable_checks.append(not gaps.missing_exception_handling)
        if output_count > 0:
            applicable_checks.append(not gaps.missing_output_definition)

        if not applicable_checks:
            return 1.0

        return round(sum(applicable_checks) / len(applicable_checks), 4)
