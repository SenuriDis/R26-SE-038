"""
The final integration point of this whole extension.

Merges four independently-testable pieces into one JSON structure per
function:
  - ast_metrics        (from your existing AST engine, via FunctionInfo)
  - risk_analysis       (from your existing RiskDetector, unchanged)
  - specification_metrics  (Phase 4)
  - gap_analysis          (Phase 3)

This is what your ML risk model and downstream LLM stages should
consume -- one flat list of per-function records, plus a project-level
summary for dashboards/reporting.

Functions that are documented but not implemented have no ast_metrics
or risk_analysis (there's no code to measure) -- both are set to None
rather than zeros, so downstream consumers can distinguish "this
function scored 0 complexity" from "this function doesn't exist".
"""

from dataclasses import asdict
from typing import Dict, List

from src.requirement_analysis.code_requirement_mapper import CodeRequirementMapper, MappingStatus
from src.requirement_analysis.gap_detector import GapDetector
from src.requirement_analysis.specification_metrics import SpecificationMetricsCalculator
from src.requirement_analysis.models import Requirement

_STATUS_TO_SUMMARY_KEY = {
    MappingStatus.DOCUMENTED_IMPLEMENTED.value: "documented_and_implemented",
    MappingStatus.DOCUMENTED_MISSING.value: "documented_but_missing",
    MappingStatus.IMPLEMENTED_UNDOCUMENTED.value: "implemented_but_undocumented",
}


class FeatureMatrixBuilder:
    def __init__(self):
        self._mapper = CodeRequirementMapper()
        self._gap_detector = GapDetector()
        self._spec_calculator = SpecificationMetricsCalculator()

    def build(
        self,
        function_infos: List,
        requirements: List[Requirement],
        risk_results: Dict[str, dict],
    ) -> dict:
        mappings = self._mapper.map(function_infos, requirements)

        function_records = [
            self._build_function_record(mapping, risk_results) for mapping in mappings
        ]

        return {
            "project_summary": self._build_summary(function_records),
            "functions": function_records,
        }

    def _build_function_record(self, mapping, risk_results: Dict[str, dict]) -> dict:
        gaps = self._gap_detector.detect(mapping)
        spec_metrics = self._spec_calculator.calculate(mapping, gaps)

        function_info = mapping.function_info
        ast_metrics = None
        risk_analysis = None

        if function_info is not None:
            ast_metrics = {
                "cyclomatic_complexity": function_info.cyclomatic_complexity,
                "nesting_depth": function_info.nesting_depth,
                "dependency_count": function_info.dependency_count,
                "lines_of_code": function_info.lines_of_code,
            }
            risk_analysis = risk_results.get(mapping.function_name)

        return {
            "function_name": mapping.function_name,
            "mapping_status": mapping.status.value,
            "ast_metrics": ast_metrics,
            "risk_analysis": risk_analysis,
            "specification_metrics": asdict(spec_metrics),
            "gap_analysis": asdict(gaps),
        }

    @staticmethod
    def _build_summary(function_records: List[dict]) -> dict:
        total = len(function_records)
        status_counts = {
            "documented_and_implemented": 0,
            "documented_but_missing": 0,
            "implemented_but_undocumented": 0,
        }

        coverage_scores = []
        for record in function_records:
            status_counts[_STATUS_TO_SUMMARY_KEY[record["mapping_status"]]] += 1
            coverage_scores.append(record["specification_metrics"]["specification_coverage_score"])

        average_coverage = round(sum(coverage_scores) / total, 4) if total else 0.0

        return {
            "total_functions": total,
            **status_counts,
            "average_specification_coverage": average_coverage,
        }
