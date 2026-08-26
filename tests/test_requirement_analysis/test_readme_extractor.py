"""
Tests for Phase 9: ReadmeRequirementExtractor.

Run with: pytest tests/test_requirement_analysis/test_readme_extractor.py -v
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.requirement_analysis.readme_extractor import ReadmeRequirementExtractor

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
FIXTURE_PROJECT = os.path.join(BASE_DIR, "sample_code", "documented_library_project")


def test_extracts_a_properly_documented_function_from_readme():
    extractor = ReadmeRequirementExtractor()
    requirements = extractor.extract(
        FIXTURE_PROJECT, known_function_names={"convert_currency", "undocumented_helper"}
    )

    by_name = {r.function_name: r for r in requirements}
    assert "convert_currency" in by_name

    req = by_name["convert_currency"]
    assert {i.name for i in req.inputs} == {"amount", "rate"}
    assert req.exceptions == ["ValueError"]
    assert "float" in req.expected_output.lower()


def test_does_not_fabricate_a_requirement_for_undocumented_function():
    extractor = ReadmeRequirementExtractor()
    requirements = extractor.extract(
        FIXTURE_PROJECT, known_function_names={"convert_currency", "undocumented_helper"}
    )
    names = {r.function_name for r in requirements}

    # undocumented_helper is a real function but has no README section
    assert "undocumented_helper" not in names


def test_ignores_headers_that_dont_match_a_known_function_name(tmp_path):
    (tmp_path / "README.md").write_text(
        "# My Project\n\n"
        "## Installation\n\n"
        "pip install my-project\n\n"
        "## License\n\nMIT\n"
    )
    extractor = ReadmeRequirementExtractor()
    requirements = extractor.extract(str(tmp_path), known_function_names={"do_thing"})

    # "Installation" and "License" are headers, but not function names --
    # neither should produce a fabricated requirement
    assert requirements == []


def test_returns_empty_list_when_no_readme_exists(tmp_path):
    extractor = ReadmeRequirementExtractor()
    requirements = extractor.extract(str(tmp_path), known_function_names={"anything"})
    assert requirements == []


def test_real_repo_with_no_function_level_readme_finds_nothing():
    # Regression / honesty check: programiz/Calculator's real README has
    # zero function-level content (verified manually). This test uses a
    # local copy of that exact README to confirm the extractor doesn't
    # invent anything from installation instructions and a video link.
    calculator_dir_readme = (
        "# Calculator\n"
        "Create your own Python Calculator App using Python and tkinter.\n\n"
        "Video Link: [link]\n\n"
        "## Create Standalone Executable\n\n"
        "pip install pyinstaller\n"
        "pyinstaller --onefile -w calc.py\n"
    )
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        with open(os.path.join(tmp_dir, "README.md"), "w") as f:
            f.write(calculator_dir_readme)

        extractor = ReadmeRequirementExtractor()
        requirements = extractor.extract(
            tmp_dir,
            known_function_names={
                "__init__", "bind_keys", "create_special_buttons",
                "create_digit_buttons", "create_operator_buttons",
                "square", "sqrt", "evaluate", "clear",
            },
        )

        assert requirements == []
