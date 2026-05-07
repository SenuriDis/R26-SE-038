import subprocess
import json
import os
import sys
import datetime

# CONFIGURATION
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
SRC_DIR      = os.path.join(BASE_DIR, "src")
TESTS_DIR    = os.path.join(BASE_DIR, "tests")
REPORTS_DIR  = os.path.join(BASE_DIR, "reports")
REPORT_FILE  = os.path.join(REPORTS_DIR, "evaluation_report.json")

os.makedirs(REPORTS_DIR, exist_ok=True)


def run_tests():
    print("\n" + "="*60)
    print("  TEST EXECUTION & EVALUATION PIPELINE")
    print("  Component: Test Execution and Evaluation")
    print("="*60)
    print(f"\n[1/3] Running PyTest with coverage on: {TESTS_DIR}\n")

    cmd = [
        sys.executable, "-m", "pytest",
        TESTS_DIR,
        "--tb=short",           
        "-v",                   
        f"--cov={SRC_DIR}",     
        "--cov-report=term",    
        "--cov-report=json:reports/coverage.json", 
        "-q",
    ]

    result = subprocess.run(
        cmd,
        capture_output=False,
        text=True,
        cwd=BASE_DIR
    )
    return result.returncode


