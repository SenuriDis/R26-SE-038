"""
Mines git for the four process metrics C2 wants and C1 cannot know:
commit_frequency, author_count, bug_history, days_since_last_change.

These matter more than their count suggests. They feed six of C2's engineered
features, and three of the model's top eight by importance are driven by them
(change_risk, bug_history, commit_frequency). Left at defaults, every function
looks equally untouched and the model's ranking collapses into noise.

Granularity is per function, not per file: `git log -L <start>,<end>:<file>`
follows a specific line range backwards through history, tracking it as it
moves. Two functions in the same file get genuinely different numbers.

Everything degrades quietly. A target that isn't a git repo, an untracked
file, a missing git binary, or a command that runs too long all fall back to
the same defaults the pipeline used before, so analysis never fails just
because history is unavailable.
"""

import re
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional

# Marks a commit header line in `git log -L` output, which otherwise
# interleaves diff hunks we don't care about. \x01 won't occur in source.
_REC = "\x01"
_SEP = "\x1f"
_FORMAT = f"{_REC}%H{_SEP}%an{_SEP}%ae{_SEP}%ct{_SEP}%s"

# A commit is counted as a bug fix when its subject matches this. Deliberately
# broad -- under-counting fixes is worse here than over-counting, since the
# feature is a risk signal rather than a precise defect count.
_BUG_PATTERN = re.compile(
    r"\b(fix(e[sd])?|bug|hotfix|patch|defect|regression|crash|broken|"
    r"revert|issue|fault|repair|correct(ed|ion)?)\b",
    re.IGNORECASE,
)

_DEFAULTS = {
    "commit_frequency": 0,
    "author_count": 1,
    "bug_history": 0,
    "days_since_last_change": 999,
}

# Per-function git log is the expensive part of stage 1. Cache on the exact
# query so re-analysing a file, or two functions sharing a range, costs once.
_cache: Dict[tuple, Dict] = {}


class GitHistoryUnavailable(Exception):
    """Raised once, at setup, when history cannot be mined at all."""


def _run(args: List[str], cwd: Path, timeout: float = 30.0) -> Optional[str]:
    """Run a git command, returning stdout or None if it fails or hangs."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            errors="replace",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None

    if result.returncode != 0:
        return None
    return result.stdout


def find_repo_root(path: Path) -> Optional[Path]:
    """The git repo containing `path`, or None if it isn't in one."""
    start = path if path.is_dir() else path.parent
    out = _run(["rev-parse", "--show-toplevel"], cwd=start)
    if not out:
        return None
    return Path(out.strip())


def _parse_log(output: str) -> List[Dict]:
    """Pull commit records out of `git log -L` output, ignoring diff lines."""
    commits = []
    seen = set()

    for line in output.splitlines():
        if not line.startswith(_REC):
            continue
        parts = line[len(_REC):].split(_SEP)
        if len(parts) < 5:
            continue

        sha, author, email, timestamp, subject = parts[0], parts[1], parts[2], parts[3], parts[4]

        # `git log -L` with several ranges can repeat a commit.
        if sha in seen:
            continue
        seen.add(sha)

        try:
            when = int(timestamp)
        except ValueError:
            continue

        commits.append({
            "sha": sha,
            "author": author,
            "email": email.lower(),
            "timestamp": when,
            "subject": subject,
        })

    return commits


def _summarise(commits: List[Dict], now: Optional[float] = None) -> Dict:
    """Turn a commit list into the four C2 fields."""
    if not commits:
        return dict(_DEFAULTS)

    now = now if now is not None else time.time()

    # Identity by email where present, since the same person often commits
    # under several display names.
    authors = {c["email"] or c["author"] for c in commits}
    bug_fixes = sum(1 for c in commits if _BUG_PATTERN.search(c["subject"]))
    latest = max(c["timestamp"] for c in commits)

    days = int((now - latest) // 86400)

    return {
        "commit_frequency": len(commits),
        "author_count": max(len(authors), 1),
        "bug_history": bug_fixes,
        # Clamped to the model's own default ceiling so a very old file can't
        # become an outlier the training data never contained.
        "days_since_last_change": max(0, min(days, 999)),
    }


class GitHistoryMiner:
    """
    Mines per-function history for files inside one repository.

    Construct once per pipeline run; it resolves the repo root up front and
    reports whether mining is possible at all, so the caller can warn once
    rather than per function.
    """

    def __init__(self, target: Path, per_call_timeout: float = 30.0):
        self.repo_root = find_repo_root(Path(target).resolve())
        self.per_call_timeout = per_call_timeout
        self.available = self.repo_root is not None
        self.stats = {"mined": 0, "defaulted": 0, "cache_hits": 0}

    def _relative(self, file_path: Path) -> Optional[str]:
        try:
            return file_path.resolve().relative_to(self.repo_root).as_posix()
        except (ValueError, AttributeError):
            return None

    def mine(self, file_path: Path, start_line: int, end_line: int) -> Dict:
        """
        The four git fields for one function's line range.

        Returns the defaults unchanged whenever history can't be read, so the
        result is always safe to splat into a C2 record.
        """
        if not self.available:
            self.stats["defaulted"] += 1
            return dict(_DEFAULTS)

        relative = self._relative(Path(file_path))
        if relative is None:
            self.stats["defaulted"] += 1
            return dict(_DEFAULTS)

        key = (relative, start_line, end_line)
        if key in _cache:
            self.stats["cache_hits"] += 1
            return dict(_cache[key])

        output = _run(
            [
                "log",
                f"-L{start_line},{end_line}:{relative}",
                f"--format={_FORMAT}",
                "--no-color",
            ],
            cwd=self.repo_root,
            timeout=self.per_call_timeout,
        )

        if output is None:
            # Untracked, renamed beyond detection, or too slow. Fall back to
            # the file's own history rather than giving up entirely.
            result = self._file_level(relative)
        else:
            result = _summarise(_parse_log(output))

        if result == _DEFAULTS:
            self.stats["defaulted"] += 1
        else:
            self.stats["mined"] += 1

        _cache[key] = result
        return dict(result)

    def _file_level(self, relative: str) -> Dict:
        """Whole-file history: coarser, but far cheaper than a line range."""
        key = (relative, None, None)
        if key in _cache:
            return _cache[key]

        output = _run(
            ["log", "--follow", f"--format={_FORMAT}", "--no-color", "--", relative],
            cwd=self.repo_root,
            timeout=self.per_call_timeout,
        )

        result = dict(_DEFAULTS) if output is None else _summarise(_parse_log(output))
        _cache[key] = result
        return result
