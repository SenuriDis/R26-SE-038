import subprocess
import sys
import time
from app.coverage_runner import run_with_coverage
from app.report_generator import generate_report

def execute_tests():
    start = time.time()

    result = subprocess.run([sys.executable, "-m", "pytest"], capture_output=True, text=True)

    end = time.time()

    status = "PASS" if result.returncode == 0 else "FAIL"
    coverage = run_with_coverage()

    return generate_report(
        status=status,
        output=result.stdout,
        errors=result.stderr,
        execution_time=end - start,
        coverage=coverage
    )