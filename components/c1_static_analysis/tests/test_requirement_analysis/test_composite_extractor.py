"""
Tests for Phase 7: TypeHintRequirementExtractor and CompositeRequirementExtractor.

Run with: pytest tests/test_requirement_analysis/test_composite_extractor.py -v
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.parser.ast_parser import parse_python_file
from src.requirement_analysis.type_hint_extractor import TypeHintRequirementExtractor
from src.requirement_analysis.composite_extractor import CompositeRequirementExtractor

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
SAMPLE_FILE = os.path.join(BASE_DIR, "sample_code", "documented_library.py")


def test_type_hint_extractor_ignores_unannotated_functions():
    # documented_library.py has no type hints at all -- both functions
    # should be skipped by the type-hint extractor.
    tree, _ = parse_python_file(SAMPLE_FILE)
    requirements = TypeHintRequirementExtractor().extract(tree)
    assert requirements == []


def test_type_hint_extractor_finds_annotated_function(tmp_path):
    sample = tmp_path / "typed_sample.py"
    sample.write_text(
        "def add_numbers(a: int, b: int) -> int:\n"
        "    return a + b\n"
        "\n"
        "def untyped(x):\n"
        "    return x\n"
    )
    tree, _ = parse_python_file(str(sample))
    requirements = TypeHintRequirementExtractor().extract(tree)
    by_name = {r.function_name: r for r in requirements}

    assert "add_numbers" in by_name
    assert "untyped" not in by_name  # no annotations at all -> nothing extracted
    assert by_name["add_numbers"].inputs[0].constraint == "int"
    assert by_name["add_numbers"].expected_output == "int"


def test_composite_extractor_prefers_docstring_over_type_hints(tmp_path):
    sample = tmp_path / "mixed_sample.py"
    sample.write_text(
        "def calculate(days: int) -> float:\n"
        "    \"\"\"\n"
        "    Args:\n"
        "        days (int): must be >= 0.\n"
        "    Returns:\n"
        "        float: the result.\n"
        "    Raises:\n"
        "        ValueError: if days is negative.\n"
        "    \"\"\"\n"
        "    if days < 0:\n"
        "        raise ValueError('bad')\n"
        "    return days * 1.0\n"
    )
    tree, _ = parse_python_file(str(sample))
    requirements = CompositeRequirementExtractor().extract(tree)
    assert len(requirements) == 1

    req = requirements[0]
    # Docstring version should win -- it has exceptions, type hints alone don't.
    assert req.exceptions == ["ValueError"]


def test_composite_extractor_falls_back_to_type_hints_when_no_docstring(tmp_path):
    sample = tmp_path / "typed_only.py"
    sample.write_text(
        "def scale(value: float, factor: float) -> float:\n"
        "    return value * factor\n"
    )
    tree, _ = parse_python_file(str(sample))
    requirements = CompositeRequirementExtractor().extract(tree)
    assert len(requirements) == 1
    assert requirements[0].function_name == "scale"
    assert requirements[0].inputs[0].constraint == "float"


def test_composite_extractor_prefers_readme_over_type_hints(tmp_path):
    sample = tmp_path / "readme_priority.py"
    sample.write_text(
        "def convert(amount: float) -> float:\n"
        "    return amount\n"
    )
    tree, _ = parse_python_file(str(sample))

    from src.requirement_analysis.models import Requirement, InputConstraint

    readme_requirements = {
        "convert": Requirement(
            function_name="convert",
            inputs=[InputConstraint(name="amount", constraint="must be positive")],
            expected_output="the converted amount",
            exceptions=["ValueError"],
        )
    }

    requirements = CompositeRequirementExtractor().extract(tree, readme_requirements)
    assert len(requirements) == 1
    # README version has exceptions -- type-hint version never does --
    # so this confirms the README source won, not the type-hint fallback.
    assert requirements[0].exceptions == ["ValueError"]


def test_composite_extractor_prefers_docstring_over_readme(tmp_path):
    sample = tmp_path / "docstring_wins.py"
    sample.write_text(
        "def convert(amount):\n"
        "    \"\"\"\n"
        "    Args:\n"
        "        amount: the amount to convert\n"
        "    Raises:\n"
        "        TypeError: if amount is not numeric\n"
        "    \"\"\"\n"
        "    return amount\n"
    )
    tree, _ = parse_python_file(str(sample))

    from src.requirement_analysis.models import Requirement, InputConstraint

    readme_requirements = {
        "convert": Requirement(
            function_name="convert",
            inputs=[InputConstraint(name="amount", constraint="must be positive")],
            expected_output="",
            exceptions=["ValueError"],
        )
    }

    requirements = CompositeRequirementExtractor().extract(tree, readme_requirements)
    assert len(requirements) == 1
    # Docstring says TypeError, README says ValueError -- docstring
    # should win since it's the highest-priority source.
    assert requirements[0].exceptions == ["TypeError"]
