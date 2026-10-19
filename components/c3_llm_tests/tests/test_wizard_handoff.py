import pytest

from api.wizard_source import write_source_files


def test_wizard_source_files_are_written_under_isolated_workspace(tmp_path):
    write_source_files(tmp_path, {
        "src/sample.py": "def sample():\n    return 1\n",
        "src/__init__.py": "",
    })

    assert (tmp_path / "src" / "sample.py").read_text(encoding="utf-8").startswith("def sample")
    assert (tmp_path / "src" / "__init__.py").exists()


@pytest.mark.parametrize("unsafe_path", [
    "../outside.py",
    "/outside.py",
    "src\\..\\outside.py",
    "C:\\outside.py",
])
def test_wizard_source_files_reject_unsafe_paths(tmp_path, unsafe_path):
    with pytest.raises(ValueError, match="Invalid Python source path"):
        write_source_files(tmp_path, {unsafe_path: "print('unsafe')"})
