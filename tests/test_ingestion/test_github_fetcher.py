"""
Tests for GitHubFetcher. Uses a real network clone against GitHub's own
tiny canonical test repository (octocat/Hello-World) -- not a mock --
so this actually proves the clone step works, not just that the code
compiles.

Run with: pytest tests/test_ingestion/test_github_fetcher.py -v
"""

import os
import shutil
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest

from src.ingestion.github_fetcher import GitHubFetcher, GitHubFetchError, CLONE_BASE_DIR

TEST_REPO_URL = "https://github.com/octocat/Hello-World.git"


@pytest.fixture(autouse=True)
def cleanup():
    yield
    shutil.rmtree(CLONE_BASE_DIR, ignore_errors=True)


def test_rejects_invalid_url():
    with pytest.raises(GitHubFetchError):
        GitHubFetcher().clone("not-a-url")


def test_rejects_non_github_url():
    with pytest.raises(GitHubFetchError):
        GitHubFetcher().clone("https://gitlab.com/someone/somerepo")


def test_clones_a_real_public_repo():
    local_path = GitHubFetcher().clone(TEST_REPO_URL)

    assert os.path.isdir(local_path)
    assert os.path.isdir(os.path.join(local_path, ".git"))
    # Confirm it actually pulled real content, not an empty folder
    assert len(os.listdir(local_path)) > 0


def test_second_call_reuses_existing_clone_without_error():
    first_path = GitHubFetcher().clone(TEST_REPO_URL)
    second_path = GitHubFetcher().clone(TEST_REPO_URL)  # should NOT re-clone
    assert first_path == second_path
    assert os.path.isdir(second_path)


def test_force_reclone_actually_recreates_the_folder():
    local_path = GitHubFetcher().clone(TEST_REPO_URL)
    # Drop a marker file, then force-reclone and confirm it's gone --
    # proving the folder was genuinely removed and re-cloned, not reused.
    marker = os.path.join(local_path, "marker.txt")
    with open(marker, "w") as f:
        f.write("test")

    GitHubFetcher().clone(TEST_REPO_URL, force_reclone=True)
    assert not os.path.exists(marker)
