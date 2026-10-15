"""
Works out which functions a change actually touched.

This is what makes the pipeline usable in CI. Generating tests costs roughly
45 seconds per function on Groq's free tier, so a 266-function repository is
about three and a half hours -- far past any sane CI timeout. Scoping to the
diff turns that into seconds, and it is also more useful: tests for the code
someone just wrote.

The unit is a *line range*, not a file. A one-line edit in a 500-line module
should pull in the one function that changed, not all forty.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# `@@ -old,count +new,count @@` -- only the new-side range matters, since we
# care about what the code looks like now.
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


class DiffUnavailable(Exception):
    """Raised when a diff cannot be computed, so the caller can fall back."""


def _run(args: List[str], cwd: Path, timeout: float = 60.0) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(cwd), capture_output=True, text=True,
            timeout=timeout, errors="replace",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None

    return result.stdout if result.returncode == 0 else None


def resolve_base_ref(repo_root: Path, explicit: Optional[str] = None) -> Optional[str]:
    """
    Decide what to diff against.

    Order: an explicit ref, then GitHub Actions' own environment, then the
    default branch, then the previous commit. Returns None when nothing
    usable is found -- a shallow clone with a single commit, typically.
    """
    if explicit:
        return explicit

    # On a pull_request event Actions sets this to the target branch name.
    base_ref = os.environ.get("GITHUB_BASE_REF")
    if base_ref:
        for candidate in (f"origin/{base_ref}", base_ref):
            if _run(["rev-parse", "--verify", candidate], repo_root) is not None:
                return candidate

    for candidate in ("origin/main", "origin/master", "main", "master"):
        if _run(["rev-parse", "--verify", candidate], repo_root) is not None:
            # Only useful if it is actually a different commit from HEAD.
            head = _run(["rev-parse", "HEAD"], repo_root)
            other = _run(["rev-parse", candidate], repo_root)
            if head and other and head.strip() != other.strip():
                return candidate

    if _run(["rev-parse", "--verify", "HEAD~1"], repo_root) is not None:
        return "HEAD~1"

    return None


def changed_line_ranges(
    repo_root: Path,
    base_ref: str,
    include_untracked: bool = True,
) -> Dict[str, List[Tuple[int, int]]]:
    """
    Map each changed Python file to the line ranges that changed in it.

    Uses `...` (merge-base) rather than `..`, so a long-lived branch reports
    only its own changes and not everything that landed on the base since.
    """
    ranges: Dict[str, List[Tuple[int, int]]] = {}

    diff = _run(
        ["diff", "--unified=0", "--no-color", f"{base_ref}...HEAD", "--", "*.py"],
        repo_root,
    )
    if diff is None:
        # Merge-base form fails on unrelated histories; fall back to a plain diff.
        diff = _run(
            ["diff", "--unified=0", "--no-color", base_ref, "--", "*.py"],
            repo_root,
        )
    if diff is None:
        raise DiffUnavailable(f"could not diff against {base_ref}")

    current: Optional[str] = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[4:].strip()
            # "+++ b/src/thing.py", or /dev/null for a deletion.
            current = None if path == "/dev/null" else path[2:] if path.startswith("b/") else path
            if current:
                ranges.setdefault(current, [])
            continue

        if current is None:
            continue

        match = _HUNK.match(line)
        if match:
            start = int(match.group(1))
            count = int(match.group(2)) if match.group(2) is not None else 1
            if count == 0:
                # A pure deletion: nothing on the new side to attribute.
                continue
            ranges[current].append((start, start + count - 1))

    if include_untracked:
        untracked = _run(["ls-files", "--others", "--exclude-standard", "--", "*.py"], repo_root)
        if untracked:
            for path in untracked.splitlines():
                path = path.strip()
                if path:
                    # A brand new file counts as entirely changed.
                    ranges.setdefault(path, []).append((1, 10**9))

    # Files that appeared only as deletions have no ranges; drop them.
    return {path: spans for path, spans in ranges.items() if spans}


def overlaps(function_span: Tuple[int, int], spans: List[Tuple[int, int]]) -> bool:
    """True when a function's line range intersects any changed range."""
    start, end = function_span
    return any(start <= span_end and end >= span_start for span_start, span_end in spans)


def changed_files(ranges: Dict[str, List[Tuple[int, int]]], repo_root: Path) -> Set[Path]:
    """Absolute paths of the changed Python files."""
    return {(repo_root / path).resolve() for path in ranges}
