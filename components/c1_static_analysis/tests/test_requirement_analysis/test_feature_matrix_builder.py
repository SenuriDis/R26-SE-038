"""
Tests for Phase 5: FeatureMatrixBuilder -- the full pipeline, end to end,
using your real ast_parser, extractor, metrics, adapter, and
risk_detector modules together for the first time.

Run with: pytest tests/test_requirement_analysis/test_feature_matrix_builder.py -v
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.parser.ast_parser import parse_python_file
from src.metrics.function_complexity_calculator import FunctionComplexityCalculator
from src.extractor.dependency_extractor import DependencyExtractor
from src.adapter.function_info_adapter import FunctionInfoAdapter
from src.risk.risk_detector import RiskDetector
from src.requirement_analysis.parsers.parser_factory import RequirementParserFactory
from src.integration.feature_matrix_builder import FeatureMatrixBuilder

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")


def _build_unified_output(source_file, requirement_file):
    tree, _source = parse_python_file(source_file)
    function_complexities = FunctionComplexityCalculator().extract(tree)
    dependencies = DependencyExtractor().extract(tree)

    function_infos = FunctionInfoAdapter().build(tree, function_complexities, dependencies)
    risk_results = RiskDetector(function_complexities, dependencies).detect_risk()

    parser = RequirementParserFactory.get_parser(requirement_file)
    requirements = parser.parse(requirement_file)

    return FeatureMatrixBuilder().build(function_infos, requirements, risk_results)


def test_calculator_produces_all_three_mapping_states():
    source = os.path.join(BASE_DIR, "sample_code", "calculator.py")
    reqs = os.path.join(BASE_DIR, "examples", "calculator_requirements.json")
    output = _build_unified_output(source, reqs)

    records = {r["function_name"]: r for r in output["functions"]}
    assert set(records) == {"calculate_fee", "enrol_student", "undocumented_helper"}

    summary = output["project_summary"]
    assert summary["total_functions"] == 3
    assert summary["documented_and_implemented"] == 1
    assert summary["documented_but_missing"] == 1
    assert summary["implemented_but_undocumented"] == 1


def test_documented_and_implemented_record_has_full_data():
    source = os.path.join(BASE_DIR, "sample_code", "calculator.py")
    reqs = os.path.join(BASE_DIR, "examples", "calculator_requirements.json")
    output = _build_unified_output(source, reqs)
    record = {r["function_name"]: r for r in output["functions"]}["calculate_fee"]

    assert record["mapping_status"] == "documented_implemented"
    assert record["ast_metrics"] is not None
    assert record["ast_metrics"]["cyclomatic_complexity"] >= 2
    assert record["risk_analysis"] is not None
    assert record["risk_analysis"]["risk_level"] in {"Low", "Medium", "High"}
    assert record["specification_metrics"]["specification_coverage_score"] == 1.0
    assert record["gap_analysis"]["missing_input_validation"] is False


def test_documented_but_missing_record_has_no_ast_or_risk_data():
    source = os.path.join(BASE_DIR, "sample_code", "calculator.py")
    reqs = os.path.join(BASE_DIR, "examples", "calculator_requirements.json")
    output = _build_unified_output(source, reqs)
    record = {r["function_name"]: r for r in output["functions"]}["enrol_student"]

    assert record["mapping_status"] == "documented_missing"
    assert record["ast_metrics"] is None
    assert record["risk_analysis"] is None
    assert record["gap_analysis"]["missing_function"] is True


def test_discount_pipeline_flags_low_coverage_via_full_stack():
    source = os.path.join(BASE_DIR, "sample_code", "discount.py")
    reqs = os.path.join(BASE_DIR, "examples", "discount_requirements.json")
    output = _build_unified_output(source, reqs)
    record = {r["function_name"]: r for r in output["functions"]}["apply_discount"]

    assert record["ast_metrics"] is not None
    assert record["risk_analysis"] is not None
    assert record["specification_metrics"]["specification_coverage_score"] < 1.0
    assert record["gap_analysis"]["missing_input_validation"] is True
    assert record["gap_analysis"]["missing_exception_handling"] is True
