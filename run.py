import subprocess
import json
import os
import sys
import datetime

# Configuration
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
SRC_DIR      = os.path.join(BASE_DIR, "src")
TESTS_DIR    = os.path.join(BASE_DIR, "tests")
REPORTS_DIR  = os.path.join(BASE_DIR, "reports")
REPORT_FILE  = os.path.join(REPORTS_DIR, "evaluation_report.json")

os.makedirs(REPORTS_DIR, exist_ok=True)

def run_tests():
    print("\n" + "="*60)
    print("  TEST EXECUTION & EVALUATION PIPELINE")
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

# Coverage report
def parse_coverage():
    cov_path = os.path.join(REPORTS_DIR, "coverage.json")
    if not os.path.exists(cov_path):
        return {"error": "coverage.json not found — ensure pytest-cov is installed"}

    with open(cov_path, "r") as f:
        cov_data = json.load(f)

    totals = cov_data.get("totals", {})
    return {
        "statements_total"  : totals.get("num_statements", 0),
        "statements_covered": totals.get("covered_lines", 0),
        "statements_missed" : totals.get("missing_lines", 0),
        "branch_total"      : totals.get("num_branches", 0),
        "branch_covered"    : totals.get("covered_branches", 0),
        "statement_coverage_pct": round(totals.get("percent_covered", 0.0), 2),
    }

def parse_pytest_results():
    """JSON report mode to get structured pass/fail data."""
    json_report_path = os.path.join(REPORTS_DIR, "pytest_results.json")

    cmd = [
        sys.executable, "-m", "pytest",
        TESTS_DIR,
        f"--json-report",
        f"--json-report-file={json_report_path}",
        "-q",
        "--tb=no",   
        f"--cov={SRC_DIR}",
        "--cov-report=",  
    ]

    subprocess.run(cmd, capture_output=True, cwd=BASE_DIR)

    if not os.path.exists(json_report_path):
        return {"error": "pytest JSON report not generated"}

    with open(json_report_path, "r") as f:
        data = json.load(f)

    summary = data.get("summary", {})
    tests   = data.get("tests", [])

    failed_tests = [
        {"name": t["nodeid"], "outcome": t["outcome"],
         "message": t.get("call", {}).get("longrepr", "")[:300]}
        for t in tests if t.get("outcome") != "passed"
    ]

    return {
        "total"   : summary.get("total", 0),
        "passed"  : summary.get("passed", 0),
        "failed"  : summary.get("failed", 0),
        "errors"  : summary.get("error", 0),
        "skipped" : summary.get("skipped", 0),
        "pass_rate_pct": round(
            summary.get("passed", 0) / summary.get("total", 1) * 100, 2
        ),
        "failed_tests": failed_tests,
    }
