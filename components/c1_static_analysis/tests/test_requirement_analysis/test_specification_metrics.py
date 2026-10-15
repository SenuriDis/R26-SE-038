"""
Tests for Phase 4: SpecificationMetricsCalculator.

Run with: pytest tests/test_requirement_analysis/test_specification_metrics.py -v
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.parser.ast_parser import parse_python_file
from src.metrics.function_complexity_calculator import FunctionComplexityCalculator
from src.extractor.dependency_extractor import DependencyExtractor
from src.adapter.function_info_adapter import FunctionInfoAdapter
from src.requirement_analysis.parsers.parser_factory import RequirementParserFactory
from src.requirement_analysis.code_requirement_mapper import CodeRequirementMapper
from src.requirement_analysis.gap_detector import GapDetector
from src.requirement_analysis.specification_metrics import SpecificationMetricsCalculator

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")


def _mapping_results(source_file, requirement_file):
    tree, _source = parse_python_file(source_file)
    function_complexities = FunctionComplexityCalculator().extract(tree)
    dependencies = DependencyExtractor().extract(tree)
    function_infos = FunctionInfoAdapter().build(tree, function_complexities, dependencies)

    parser = RequirementParserFactory.get_parser(requirement_file)
    requirements = parser.parse(requirement_file)

    results = CodeRequirementMapper().map(function_infos, requirements)
    return {r.function_name: r for r in results}


def test_fully_compliant_function_scores_1_0():
    source = os.path.join(BASE_DIR, "sample_code", "calculator.py")
    reqs = os.path.join(BASE_DIR, "examples", "calculator_requirements.json")
    mapping = _mapping_results(source, reqs)["calculate_fee"]

    gaps = GapDetector().detect(mapping)
    metrics = SpecificationMetricsCalculator().calculate(mapping, gaps)

    assert metrics.has_documentation_mapping is True
    assert metrics.input_requirements_count == 1
    assert metrics.output_requirements_count == 1
    assert metrics.exception_requirements_count == 1
    assert metrics.specification_coverage_score == 1.0


def test_partially_compliant_function_scores_between_0_and_1():
    source = os.path.join(BASE_DIR, "sample_code", "discount.py")
    reqs = os.path.join(BASE_DIR, "examples", "discount_requirements.json")
    mapping = _mapping_results(source, reqs)["apply_discount"]

    gaps = GapDetector().detect(mapping)
    metrics = SpecificationMetricsCalculator().calculate(mapping, gaps)

    # Only output_definition is satisfied out of 3 applicable checks
    assert metrics.has_documentation_mapping is True
    assert metrics.specification_coverage_score == round(1 / 3, 4)


def test_missing_function_scores_0_0_but_counts_are_preserved():
    source = os.path.join(BASE_DIR, "sample_code", "calculator.py")
    reqs = os.path.join(BASE_DIR, "examples", "calculator_requirements.json")
    mapping = _mapping_results(source, reqs)["enrol_student"]

    gaps = GapDetector().detect(mapping)
    metrics = SpecificationMetricsCalculator().calculate(mapping, gaps)

    assert metrics.has_documentation_mapping is False
    assert metrics.specification_coverage_score == 0.0
    # The requirement counts should still reflect what WAS documented,
    # even though nothing was implemented.
    assert metrics.input_requirements_count == 1
    assert metrics.exception_requirements_count == 1


def test_undocumented_function_has_zero_counts_and_zero_score():
    source = os.path.join(BASE_DIR, "sample_code", "calculator.py")
    reqs = os.path.join(BASE_DIR, "examples", "calculator_requirements.json")
    mapping = _mapping_results(source, reqs)["undocumented_helper"]

    gaps = GapDetector().detect(mapping)
    metrics = SpecificationMetricsCalculator().calculate(mapping, gaps)

    assert metrics.has_documentation_mapping is False
    assert metrics.input_requirements_count == 0
    assert metrics.output_requirements_count == 0
    assert metrics.exception_requirements_count == 0
    assert metrics.specification_coverage_score == 0.0
