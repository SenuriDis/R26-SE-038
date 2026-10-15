"""
Tests for Phase 3: GapDetector.

Covers all four situations the detector has to handle:
1. A clean, fully-compliant function (calculate_fee) -> no gaps.
2. A function with real gaps -- no validation, no exception (apply_discount).
3. A documented but unimplemented function (enrol_student).
4. An implemented but undocumented function (undocumented_helper).

Run with: pytest tests/test_requirement_analysis/test_gap_detector.py -v
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


def test_compliant_function_has_no_gaps():
    source = os.path.join(BASE_DIR, "sample_code", "calculator.py")
    reqs = os.path.join(BASE_DIR, "examples", "calculator_requirements.json")
    by_name = _mapping_results(source, reqs)

    gaps = GapDetector().detect(by_name["calculate_fee"])

    assert gaps.missing_input_validation is False    # `if days < 0` covers it
    assert gaps.missing_exception_handling is False   # raises ValueError
    assert gaps.missing_output_definition is False    # returns a value
    assert gaps.missing_function is False
    assert gaps.missing_requirement_coverage is False


def test_noncompliant_function_flags_real_gaps():
    source = os.path.join(BASE_DIR, "sample_code", "discount.py")
    reqs = os.path.join(BASE_DIR, "examples", "discount_requirements.json")
    by_name = _mapping_results(source, reqs)

    gaps = GapDetector().detect(by_name["apply_discount"])

    assert gaps.missing_input_validation is True      # no `if` checks `percentage`
    assert gaps.missing_exception_handling is True     # no `raise` at all
    assert gaps.missing_output_definition is False     # it does return a value
    assert gaps.missing_function is False
    assert gaps.missing_requirement_coverage is False


def test_documented_but_missing_function_flags_missing_function():
    source = os.path.join(BASE_DIR, "sample_code", "calculator.py")
    reqs = os.path.join(BASE_DIR, "examples", "calculator_requirements.json")
    by_name = _mapping_results(source, reqs)

    gaps = GapDetector().detect(by_name["enrol_student"])

    assert gaps.missing_function is True
    assert gaps.missing_input_validation is True
    assert gaps.missing_exception_handling is True
    assert gaps.missing_output_definition is True
    assert gaps.missing_requirement_coverage is False   # it IS documented


def test_implemented_but_undocumented_function_flags_coverage_only():
    source = os.path.join(BASE_DIR, "sample_code", "calculator.py")
    reqs = os.path.join(BASE_DIR, "examples", "calculator_requirements.json")
    by_name = _mapping_results(source, reqs)

    gaps = GapDetector().detect(by_name["undocumented_helper"])

    assert gaps.missing_requirement_coverage is True
    assert gaps.missing_function is False
    assert gaps.missing_input_validation is False
    assert gaps.missing_exception_handling is False
    assert gaps.missing_output_definition is False
