"""
Unit tests for the requirement parsers (carried over from Phase 1,
import path updated to match src.requirement_analysis).

Run with: pytest tests/test_requirement_analysis/test_parsers.py -v
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.requirement_analysis.parsers.parser_factory import RequirementParserFactory

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "examples")


def test_json_parser_extracts_single_requirement():
    path = os.path.join(EXAMPLES_DIR, "calculate_fee.json")
    parser = RequirementParserFactory.get_parser(path)
    requirements = parser.parse(path)

    assert len(requirements) == 1
    req = requirements[0]
    assert req.function_name == "calculate_fee"
    assert req.inputs[0].name == "days"
    assert req.inputs[0].constraint == ">=0"
    assert req.expected_output == "fee amount"
    assert req.exceptions == ["ValueError"]


def test_txt_parser_extracts_single_requirement():
    path = os.path.join(EXAMPLES_DIR, "calculate_fee.txt")
    parser = RequirementParserFactory.get_parser(path)
    requirements = parser.parse(path)

    assert len(requirements) == 1
    req = requirements[0]
    assert req.function_name == "calculate_fee"
    assert req.inputs[0].name == "days"
    assert ">=" in req.inputs[0].constraint


def test_txt_parser_handles_multiple_blocks():
    path = os.path.join(EXAMPLES_DIR, "multi_function.txt")
    parser = RequirementParserFactory.get_parser(path)
    requirements = parser.parse(path)

    assert len(requirements) == 2
    names = {r.function_name for r in requirements}
    assert names == {"calculate_fee", "enrol_student"}


def test_factory_rejects_unsupported_extension():
    with pytest.raises(ValueError):
        RequirementParserFactory.get_parser("requirements.yaml")


def test_json_parser_raises_on_missing_function_name(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text('{"expected_output": "x"}')
    parser = RequirementParserFactory.get_parser(str(bad_file))
    with pytest.raises(ValueError):
        parser.parse(str(bad_file))
