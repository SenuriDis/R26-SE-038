import os
import shutil
import subprocess


def clone_repository(repo_url):
    """
    Clone a GitHub repository and return local path.
    """

    repo_name = repo_url.rstrip("/").split("/")[-1]

    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]

    clone_path = os.path.join("uploads", repo_name)

    # Delete old copy if exists
    if os.path.exists(clone_path):
        shutil.rmtree(clone_path)

    subprocess.run(
        ["git", "clone", repo_url, clone_path],
        check=True
    )

    return clone_path