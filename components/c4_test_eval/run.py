import subprocess
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
IMAGE_NAME = "test-eval"

def main():
    # Build the Docker image
    build_cmd = ["docker", "build", "-t", IMAGE_NAME, "."]
    build_result = subprocess.run(build_cmd, cwd=BASE_DIR, capture_output=True)

    if build_result.returncode != 0:
        print("\n[ERROR] Docker build failed.")
        print(build_result.stderr.decode("utf-8", errors="ignore"))
        sys.exit(build_result.returncode)

    os.makedirs(REPORTS_DIR, exist_ok=True)

    # Run the Docker container
    run_cmd = [
        "docker", "run", "--rm",
        "-v", f"{REPORTS_DIR}:/app/reports",
        IMAGE_NAME
    ]
    
    run_result = subprocess.run(run_cmd, cwd=BASE_DIR)

    sys.exit(run_result.returncode)

if __name__ == "__main__":
    main()