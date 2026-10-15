"""
Integration test for Phase 2.

Runs the REAL uploaded AST modules (ast_parser, function_complexity_calculator,
dependency_extractor) end to end, feeds their output into FunctionInfoAdapter,
then checks CodeRequirementMapper correctly classifies all three states:
documented+implemented, documented+missing, implemented+undocumented.

Run with: pytest tests/test_requirement_analysis/test_mapper_integration.py -v
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.parser.ast_parser import parse_python_file
from src.metrics.function_complexity_calculator import FunctionComplexityCalculator
from src.extractor.dependency_extractor import DependencyExtractor
from src.adapter.function_info_adapter import FunctionInfoAdapter
from src.requirement_analysis.parsers.parser_factory import RequirementParserFactory
from src.requirement_analysis.code_requirement_mapper import CodeRequirementMapper, MappingStatus

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
SAMPLE_CODE = os.path.join(BASE_DIR, "sample_code", "calculator.py")
REQUIREMENTS = os.path.join(BASE_DIR, "examples", "calculator_requirements.json")


def _build_function_infos():
    tree, _source = parse_python_file(SAMPLE_CODE)
    function_complexities = FunctionComplexityCalculator().extract(tree)
    dependencies = DependencyExtractor().extract(tree)
    return FunctionInfoAdapter().build(tree, function_complexities, dependencies)


def _mapping_results():
    function_infos = _build_function_infos()
    parser = RequirementParserFactory.get_parser(REQUIREMENTS)
    requirements = parser.parse(REQUIREMENTS)
    results = CodeRequirementMapper().map(function_infos, requirements)
    return {r.function_name: r for r in results}


def test_adapter_extracts_both_functions_with_real_ast_nodes():
    function_infos = _build_function_infos()
    names = {fi.name for fi in function_infos}
    assert names == {"calculate_fee", "undocumented_helper"}

    fee_fn = next(fi for fi in function_infos if fi.name == "calculate_fee")
    assert isinstance(fee_fn.ast_node.name, str)          # real ast.FunctionDef node
    assert fee_fn.cyclomatic_complexity >= 2              # base 1 + the if
    assert fee_fn.lines_of_code > 0


def test_documented_and_implemented_function_is_classified_correctly():
    by_name = _mapping_results()
    result = by_name["calculate_fee"]

    assert result.status == MappingStatus.DOCUMENTED_IMPLEMENTED
    assert result.function_info is not None
    assert result.requirement is not None
    assert result.requirement.exceptions == ["ValueError"]


def test_documented_but_missing_function_is_classified_correctly():
    by_name = _mapping_results()
    result = by_name["enrol_student"]

    assert result.status == MappingStatus.DOCUMENTED_MISSING
    assert result.function_info is None
    assert result.requirement is not None


def test_implemented_but_undocumented_function_is_classified_correctly():
    by_name = _mapping_results()
    result = by_name["undocumented_helper"]

    assert result.status == MappingStatus.IMPLEMENTED_UNDOCUMENTED
    assert result.function_info is not None
    assert result.requirement is None
