import subprocess
import json
import os
import sys
import datetime
import sqlite3
import re

# Configuration
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
SRC_DIR      = os.path.join(BASE_DIR, "src")
TESTS_DIR    = os.path.join(BASE_DIR, "tests")
REPORTS_DIR  = os.path.join(BASE_DIR, "reports")
REPORT_FILE  = os.path.join(REPORTS_DIR, "evaluation_report.json")
PYTEST_REPORT_FILE = os.path.join(REPORTS_DIR, "pytest_results.json")
EXECUTION_LOG_FILE = os.path.join(REPORTS_DIR, "execution.log")

os.makedirs(REPORTS_DIR, exist_ok=True)

def run_tests():
    print("\n" + "="*60)
    print("  TEST EXECUTION & EVALUATION PIPELINE (DOCKER)")
    print("="*60)
    print(f"\n[1/4] Running PyTest with coverage on: {TESTS_DIR}\n")

    cmd = [
        sys.executable, "-m", "pytest",
        TESTS_DIR,
        "--tb=short",           
        "-v",                   
        f"--cov={SRC_DIR}",     
        "--cov-branch",
        "--cov-report=term",    
        f"--cov-report=json:{os.path.join(REPORTS_DIR, 'coverage.json')}",
        "--json-report",
        f"--json-report-file={PYTEST_REPORT_FILE}",
        "-q",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=BASE_DIR
    )
    with open(EXECUTION_LOG_FILE, "w", encoding="utf-8") as log_file:
        log_file.write(result.stdout)
        log_file.write(result.stderr)
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode

def parse_coverage():
    cov_path = os.path.join(REPORTS_DIR, "coverage.json")
    if not os.path.exists(cov_path):
        return {"error": "coverage.json not found — ensure pytest-cov is installed"}

    with open(cov_path, "r") as f:
        cov_data = json.load(f)

    totals = cov_data.get("totals", {})
    
    num_branches = totals.get("num_branches", 0)
    covered_branches = totals.get("covered_branches", 0)
    branch_pct = round((covered_branches / num_branches * 100), 2) if num_branches > 0 else 0.0
    
    import ast
    files_data = cov_data.get("files", {})
    total_functions = 0
    covered_functions = 0

    for file_path, file_cov in files_data.items():
        full_path = os.path.join(BASE_DIR, file_path)
        if not os.path.exists(full_path):
            continue
            
        try:
            with open(full_path, "r", encoding="utf-8") as file_obj:
                tree = ast.parse(file_obj.read())
                
            executed_lines = set(file_cov.get("executed_lines", []))
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    total_functions += 1
                    if node.body:
                        body_start = node.body[0].lineno
                        body_end = getattr(node, 'end_lineno', body_start)
                        body_lines = set(range(body_start, body_end + 1))
                        if body_lines.intersection(executed_lines):
                            covered_functions += 1
        except Exception:
            pass

    func_pct = round((covered_functions / total_functions * 100), 2) if total_functions > 0 else 0.0

    return {
        "statements_total"  : totals.get("num_statements", 0),
        "statements_covered": totals.get("covered_lines", 0),
        "statements_missed" : totals.get("missing_lines", 0),
        "branch_total"      : num_branches,
        "branch_covered"    : covered_branches,
        "statement_coverage_pct": round(totals.get("percent_covered", 0.0), 2),
        "branch_coverage_pct": branch_pct,
        "function_coverage_pct": func_pct,
    }

def classify_failure(error_message):
    error_message = str(error_message).lower()
    if "assertionerror" in error_message or "assert " in error_message:
        return "Real Defect"
    elif "syntaxerror" in error_message or "typeerror" in error_message or "valueerror" in error_message or "attributeerror" in error_message or "nameerror" in error_message:
        return "Invalid AI Test"
    elif "importerror" in error_message or "modulenotfounderror" in error_message or "timeout" in error_message:
        return "Environment Failure"
    return "Environment Failure"

def parse_pytest_results():
    json_report_path = os.path.join(REPORTS_DIR, "pytest_results.json")

    if not os.path.exists(json_report_path):
        return {"error": "pytest JSON report not generated"}

    with open(json_report_path, "r") as f:
        data = json.load(f)

    summary = data.get("summary", {})
    tests   = data.get("tests", [])

    failed_tests = [
        {"name": t["nodeid"], "outcome": t["outcome"],
         "message": str(t.get("call", {}).get("longrepr", ""))[:300],
         "failure_type": classify_failure(t.get("call", {}).get("longrepr", ""))}
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
        ) if summary.get("total", 0) > 0 else 0.0,
        "failed_tests": failed_tests,
    }

def run_mutation_testing():
    # Create setup.cfg for mutmut to avoid CLI option errors
    setup_cfg_path = os.path.join(BASE_DIR, "setup.cfg")
    created_setup_cfg = not os.path.exists(setup_cfg_path)
    if created_setup_cfg:
        setup_cfg = "[mutmut]\npaths_to_mutate=src/\nbackup=False\nrunner=python -m pytest\ntests_dir=tests/\n"
        with open(setup_cfg_path, "w", encoding="utf-8") as config_file:
            config_file.write(setup_cfg)

    cmd = ["mutmut", "run"]
    try:
        result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
    except FileNotFoundError as exc:
        mutation_log = os.path.join(REPORTS_DIR, "mutation.log")
        with open(mutation_log, "w", encoding="utf-8") as log_file:
            log_file.write(str(exc))
        if created_setup_cfg:
            os.remove(setup_cfg_path)
        return {
            "error": "Mutation testing executable not found",
            "log_file": "reports/mutation.log",
        }
    with open(os.path.join(REPORTS_DIR, "mutation.log"), "w", encoding="utf-8") as log_file:
        log_file.write(result.stdout)
        log_file.write(result.stderr)

    # Parse sqlite cache
    cache_path = os.path.join(BASE_DIR, ".mutmut-cache")
    stats_path = os.path.join(BASE_DIR, "mutants", "mutmut-stats.json")
    if not os.path.exists(cache_path):
        if os.path.exists(stats_path):
            statuses = {}
            results = subprocess.run(["mutmut", "results"], cwd=BASE_DIR,
                                     capture_output=True, text=True)
            for status in re.findall(r":\s+(killed|survived|timeout|suspicious|no tests|skipped)\s*$",
                                     results.stdout, re.MULTILINE):
                statuses[status] = statuses.get(status, 0) + 1
            progress_totals = [
                int(match.group(2))
                for match in re.finditer(r"(?m)(\d+)/(\d+)\s+.*$", result.stdout)
                if match.group(1) == match.group(2)
            ]
            if progress_totals:
                total_mutants = max(progress_totals)
                statuses["killed"] = max(total_mutants - sum(statuses.values()), 0)
            total = sum(statuses.values())
            killed = statuses.get("killed", 0)
            survived = statuses.get("survived", 0)
            mutation_data = {
                "total_mutants": total,
                "killed_mutants": killed,
                "survived_mutants": survived,
                "mutation_score_pct": round((killed / total) * 100, 2) if total else 0.0,
                "details": statuses,
                "result_file": "mutants/mutmut-stats.json",
            }
        else:
            mutation_data = {
                "error": "Mutation cache not found",
                "exit_code": result.returncode,
                "log_file": "reports/mutation.log",
            }
    else:
        try:
            conn = sqlite3.connect(cache_path)
            c = conn.cursor()
            c.execute("SELECT status, count(*) FROM mutant GROUP BY status")
            rows = c.fetchall()
            conn.close()
            
            status_counts = {k: v for k, v in rows}
            total = sum(status_counts.values())
            killed = status_counts.get("killed", 0)
            survived = status_counts.get("survived", 0)
            mutation_score = round((killed / total) * 100, 2) if total > 0 else 0.0
            mutation_data = {
                "total_mutants": total,
                "killed_mutants": killed,
                "survived_mutants": survived,
                "mutation_score_pct": mutation_score,
                "details": status_counts
            }
        except Exception as exc:
            mutation_data = {"error": f"Failed to parse mutmut cache: {str(exc)}"}

    if created_setup_cfg:
        os.remove(setup_cfg_path)
    return mutation_data

def generate_report(exit_code, pytest_data, coverage_data, mutation_data):
    print("\n[4/4] Generating structured JSON evaluation report...\n")

    report = {
        "project"          : "LLM and ML Enhanced Software Testing System",
        "component"        : "Test Execution and Evaluation",
        "student_id"       : "IT22050908",
        "timestamp"        : datetime.datetime.now().isoformat(),
        "execution_status" : "PASS" if exit_code == 0 else "FAIL",
        "test_results"     : pytest_data,
        "coverage_metrics" : coverage_data,
        "mutation_metrics" : mutation_data,
        "evaluation_summary": {
            "pass_rate_pct"            : pytest_data.get("pass_rate_pct", 0),
            "statement_coverage_pct"   : coverage_data.get("statement_coverage_pct", 0),
            "mutation_score_pct"       : mutation_data.get("mutation_score_pct", 0) if "mutation_score_pct" in mutation_data else 0,
            "quality_grade"            : _grade(
                pytest_data.get("pass_rate_pct", 0),
                coverage_data.get("statement_coverage_pct", 0),
                mutation_data.get("mutation_score_pct", 0) if "mutation_score_pct" in mutation_data else 0
            ),
        }
    }

    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)

    return report

def _grade(pass_rate, coverage, mutation_score):
    score = (pass_rate + coverage + mutation_score) / 3
    if score >= 90: return "A — Excellent"
    if score >= 75: return "B — Good"
    if score >= 60: return "C — Acceptable"
    return "D — Needs Improvement"

def main():
    import time
    start_time = time.time()
    
    exit_code = run_tests()
    mutation_data = run_mutation_testing()
    coverage_data = parse_coverage()
    pytest_data = parse_pytest_results()
    
    report = generate_report(exit_code, pytest_data, coverage_data, mutation_data)
    
    end_time = time.time()
    execution_time = round(end_time - start_time, 1)

    # Calculate Failure Analysis metrics
    failed_tests = pytest_data.get("failed_tests", [])
    real_defects = sum(1 for t in failed_tests if t.get("failure_type") == "Real Defect")
    invalid_tests = sum(1 for t in failed_tests if t.get("failure_type") == "Invalid AI Test")
    env_failures = sum(1 for t in failed_tests if t.get("failure_type") == "Environment Failure")
    
    passed = pytest_data.get("passed", 0)
    failed = pytest_data.get("failed", 0)
    total = passed + failed

    print("================================================")
    print("       AI TEST EXECUTION & EVALUATION REPORT")
    print("================================================")
    print("\nRepository:")
    print("calculator-app") # Hardcoded
    
    print("\nTest Cases:")
    print(f"{pytest_data.get('total', 0)}")
    
    print("\nExecution:")
    print(f"Executed       : {pytest_data.get('total', 0)}")
    print(f"Passed         : {passed}")
    print(f"Failed         : {failed}")
    
    print("\nFunctional Correctness:")
    print(f"Correct        : {passed}")
    print(f"Incorrect      : {failed}")
    
    print("\nCoverage:")
    print(f"Line Coverage     : {coverage_data.get('statement_coverage_pct', 0)}%")
    print(f"Branch Coverage   : {coverage_data.get('branch_coverage_pct', 0)}%") 
    print(f"Function Coverage : {coverage_data.get('function_coverage_pct', 0)}%")
    
    mutation_total = mutation_data.get("total_mutants", 0) if isinstance(mutation_data, dict) else 0
    mutation_killed = mutation_data.get("killed_mutants", 0) if isinstance(mutation_data, dict) else 0
    mutation_survived = mutation_data.get("survived_mutants", 0) if isinstance(mutation_data, dict) else 0
    mutation_score = mutation_data.get("mutation_score_pct", 0) if isinstance(mutation_data, dict) else 0
    
    print("\nMutation Testing:")
    print(f"Total Mutants     : {mutation_total}")
    print(f"Killed Mutants    : {mutation_killed}")
    print(f"Survived Mutants  : {mutation_survived}")
    print(f"Mutation Score    : {mutation_score}%")
    
    print("\nFailure Analysis:")
    print(f"Real Defect             : {real_defects}")
    print(f"Invalid AI Test         : {invalid_tests}")
    print(f"Environment Failure     : {env_failures}")
    
    print("\nExecution Time:")
    print(f"{execution_time} seconds")
    
    print("\nEnvironment:")
    print("Docker")
    
    print("\nStatus:")
    print("COMPLETED")
    
    # We print Docker Environment: DESTROYED here since run.py handles it
    print("\nDocker Environment:")
    print("DESTROYED")
    print("================================================")

    sys.exit(exit_code)

if __name__ == "__main__":
    main()
