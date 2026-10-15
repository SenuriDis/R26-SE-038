"""
Tests for Phase 6: DocstringRequirementExtractor.

Two things are being proven here:
1. The extractor correctly parses Args/Returns/Raises from a real-style
   Google docstring, and correctly extracts NOTHING for a function
   whose docstring doesn't follow that convention.
2. The extracted Requirements plug into CodeRequirementMapper,
   GapDetector, and FeatureMatrixBuilder with ZERO changes to any of
   them -- proving the Requirement contract genuinely decouples the
   requirement SOURCE from everything downstream.

Run with: pytest tests/test_requirement_analysis/test_docstring_extractor.py -v
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.parser.ast_parser import parse_python_file
from src.metrics.function_complexity_calculator import FunctionComplexityCalculator
from src.extractor.dependency_extractor import DependencyExtractor
from src.adapter.function_info_adapter import FunctionInfoAdapter
from src.risk.risk_detector import RiskDetector
from src.requirement_analysis.docstring_extractor import DocstringRequirementExtractor
from src.integration.feature_matrix_builder import FeatureMatrixBuilder

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
SAMPLE_FILE = os.path.join(BASE_DIR, "sample_code", "documented_library.py")


def test_extractor_parses_google_style_docstring_correctly():
    tree, _ = parse_python_file(SAMPLE_FILE)
    requirements = DocstringRequirementExtractor().extract(tree)
    by_name = {r.function_name: r for r in requirements}

    assert "calculate_late_fee" in by_name
    req = by_name["calculate_late_fee"]

    assert req.inputs[0].name == "days"
    assert "must be >= 0" in req.inputs[0].constraint.lower() or ">=0" in req.inputs[0].constraint
    assert "fee" in req.expected_output.lower()
    assert req.exceptions == ["ValueError"]


def test_extractor_produces_nothing_for_undocumented_function():
    tree, _ = parse_python_file(SAMPLE_FILE)
    requirements = DocstringRequirementExtractor().extract(tree)
    names = {r.function_name for r in requirements}

    # reset_session_cache has a docstring, but no Args/Returns/Raises
    # sections -- it should NOT produce a fabricated requirement.
    assert "reset_session_cache" not in names
    assert "calculate_late_fee" in names


def test_auto_extracted_requirements_flow_through_full_pipeline_unchanged():
    tree, _ = parse_python_file(SAMPLE_FILE)
    function_complexities = FunctionComplexityCalculator().extract(tree)
    dependencies = DependencyExtractor().extract(tree)

    function_infos = FunctionInfoAdapter().build(tree, function_complexities, dependencies)
    risk_results = RiskDetector(function_complexities, dependencies).detect_risk()
    requirements = DocstringRequirementExtractor().extract(tree)

    # Same FeatureMatrixBuilder as Phase 5 -- no modification needed.
    output = FeatureMatrixBuilder().build(function_infos, requirements, risk_results)
    records = {r["function_name"]: r for r in output["functions"]}

    assert records["calculate_late_fee"]["mapping_status"] == "documented_implemented"
    assert records["calculate_late_fee"]["gap_analysis"]["missing_input_validation"] is False
    assert records["calculate_late_fee"]["gap_analysis"]["missing_exception_handling"] is False
    assert records["calculate_late_fee"]["specification_metrics"]["specification_coverage_score"] == 1.0

    # reset_session_cache has no auto-extracted requirement -> undocumented
    assert records["reset_session_cache"]["mapping_status"] == "implemented_undocumented"
