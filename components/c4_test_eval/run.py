import os
import subprocess
import sys
import uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
IMAGE_NAME = "test-eval"


def docker_run_command(container_name, reports_dir):
    return [
        "docker", "run", "--rm",
        "--name", container_name,
        "--network", "none",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--pids-limit", "256",
        "--memory", "2g",
        "--cpus", "2",
        "--tmpfs", "/tmp:rw,nosuid,nodev,size=512m",
        "--volume", f"{os.path.abspath(reports_dir)}:/app/reports",
        "--workdir", "/app",
        IMAGE_NAME,
        "python", "execute_tests.py",
    ]


def main():
    os.makedirs(REPORTS_DIR, exist_ok=True)

    try:
        build_result = subprocess.run(
            ["docker", "build", "--tag", IMAGE_NAME, "--file", "Dockerfile", "."],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=1200,
        )
    except FileNotFoundError:
        print("[ERROR] Docker CLI was not found. Install Docker and start its daemon.")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("[ERROR] Docker image build timed out after 20 minutes.")
        sys.exit(1)

    if build_result.returncode != 0:
        print("[ERROR] Docker build failed.")
        print(build_result.stdout)
        print(build_result.stderr, file=sys.stderr)
        sys.exit(build_result.returncode)

    container_name = f"test-eval-{uuid.uuid4().hex[:12]}"
    try:
        run_result = subprocess.run(
            docker_run_command(container_name, REPORTS_DIR),
            cwd=BASE_DIR,
            timeout=1800,
        )
    except FileNotFoundError:
        print("[ERROR] Docker CLI was not found while starting the evaluator.")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        cleanup = subprocess.run(
            ["docker", "rm", "--force", container_name],
            capture_output=True,
            text=True,
        )
        print("[ERROR] C4 evaluation timed out after 30 minutes.")
        if cleanup.returncode != 0:
            detail = (cleanup.stderr or cleanup.stdout).strip()
            print(f"[WARNING] Could not remove timed-out container: {detail}")
        sys.exit(124)

    sys.exit(run_result.returncode)


if __name__ == "__main__":
    main()
