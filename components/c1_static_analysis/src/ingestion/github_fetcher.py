"""
Clones a GitHub repository from a URL into a local folder, so the
existing analysis pipeline -- which already works on any local folder,
via analyze_folder() -- can run against it without anyone needing to
run `git clone` in a terminal first.

This module does NOT change how analysis itself works. It only
automates the one manual step that used to sit in front of it.
"""

import os
import re
import shutil
import stat
import subprocess

CLONE_BASE_DIR = "cloned_repos"

# Matches https://github.com/owner/repo, with or without a trailing
# .git and/or trailing slash.
_GITHUB_URL_PATTERN = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+(\.git)?/?$")


class GitHubFetchError(Exception):
    """Raised when a repository URL is invalid or cloning fails."""


class GitHubFetcher:
    def clone(self, repo_url: str, force_reclone: bool = False) -> str:
        repo_url = (repo_url or "").strip()

        if not _GITHUB_URL_PATTERN.match(repo_url):
            raise GitHubFetchError(
                f"'{repo_url}' does not look like a valid GitHub repository URL "
                f"(expected something like https://github.com/owner/repo)"
            )

        repo_name = self._extract_repo_name(repo_url)
        target_path = os.path.join(CLONE_BASE_DIR, repo_name)

        os.makedirs(CLONE_BASE_DIR, exist_ok=True)

        if os.path.isdir(target_path):
            if not force_reclone:
                # Already cloned -- reuse it rather than re-cloning every
                # single analysis request, which would be slow and
                # unnecessary for a repo that hasn't changed.
                return target_path
            self._remove_existing(target_path)

        self._run_git_clone(repo_url, target_path)

        return target_path

    @staticmethod
    def _remove_existing(target_path: str) -> None:
        # Git marks some internal .git object files read-only, especially
        # on Windows. shutil.rmtree(ignore_errors=True) silently swallows
        # the resulting PermissionError, leaving the folder non-empty --
        # which then makes the subsequent `git clone` fail with "already
        # exists and is not an empty directory". Instead, clear the
        # read-only bit and retry the removal so it actually succeeds
        # (or raises a real error if something else is wrong).
        def _on_remove_error(func, path, _exc_info):
            os.chmod(path, stat.S_IWRITE)
            func(path)

        shutil.rmtree(target_path, onerror=_on_remove_error)

    @staticmethod
    def _extract_repo_name(repo_url: str) -> str:
        name = repo_url.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]
        return name

    @staticmethod
    def _run_git_clone(repo_url: str, target_path: str) -> None:
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, target_path],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except FileNotFoundError:
            raise GitHubFetchError("git is not installed or not available on PATH")
        except subprocess.TimeoutExpired:
            raise GitHubFetchError(f"Cloning '{repo_url}' timed out after 120 seconds")

        if result.returncode != 0:
            raise GitHubFetchError(
                f"git clone failed for '{repo_url}': {result.stderr.strip()}"
            )
