from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Dict


def write_source_files(root: Path, source_files: Dict[str, str]) -> None:
    if not source_files:
        raise ValueError("source_files must contain at least one Python file.")

    size = 0
    for relative_name, contents in source_files.items():
        normalized = relative_name.replace("\\", "/")
        path = PurePosixPath(normalized)
        if (
            path.is_absolute()
            or PureWindowsPath(normalized).drive
            or not path.parts
            or ".." in path.parts
            or path.suffix != ".py"
        ):
            raise ValueError(f"Invalid Python source path: {relative_name!r}")
        if not isinstance(contents, str):
            raise ValueError(f"Source content for {relative_name!r} must be text.")

        destination = (root / Path(*path.parts)).resolve()
        destination.relative_to(root.resolve())
        size += len(contents.encode("utf-8"))
        if size > 20 * 1024 * 1024:
            raise ValueError("Source files exceed the 20 MiB pipeline handoff limit.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(contents, encoding="utf-8")
