import subprocess
import json
import os
import sys
import datetime
import sqlite3
import re
import math

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

def classify_failure_details(error_message, test_path=""):
    """Apply deterministic rules, and keep ambiguous failures available for review."""
    message = str(error_message)
    normalized = message.lower().replace("\\", "/")
    normalized_path = str(test_path).lower().replace("\\", "/")
    test_source = normalized_path.startswith("tests/") or (
        "tests/" in normalized and "test_" in normalized
    )

    if test_source and re.search(r"\b(syntaxerror|indentationerror)\b", normalized):
        return {
            "failure_type": "Invalid AI Test",
            "rule": "generated_test_syntax_error",
            "reason": "Python could not parse a generated test file.",
        }

    environment_markers = (
        "no module named",
        "modulenotfounderror",
        "pytest-cov",
        "no space left on device",
        "docker daemon",
    )
    if any(marker in normalized for marker in environment_markers):
        return {
            "failure_type": "Environment Failure",
            "rule": "known_environment_error",
            "reason": "The failure contains a known missing-dependency or execution-environment marker.",
        }

    if "assertionerror" in normalized or re.search(r"\bassert\b", normalized):
        return {
            "failure_type": "Real Software Bug",
            "rule": "assertion_mismatch",
            "reason": "An assertion failed, indicating a genuine defect in the target code logic.",
        }

    return {
        "failure_type": "Needs Review",
        "rule": "unclassified_test_failure",
        "reason": "The failure does not match a conclusive rule and needs human review.",
    }


def classify_failure(error_message, test_path=""):
    return classify_failure_details(error_message, test_path)["failure_type"]


def _report_value_text(value):
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False, default=str)


def extract_failure_evidence(test):
    phases = ("call", "setup", "teardown")
    phase = next(
        (
            candidate for candidate in phases
            if (test.get(candidate) or {}).get("outcome") in {"failed", "error"}
            or (test.get(candidate) or {}).get("longrepr")
            or (test.get(candidate) or {}).get("crash")
        ),
        "call",
    )
    phase_report = test.get(phase) or {}
    crash = phase_report.get("crash") or {}
    traceback_text = _report_value_text(phase_report.get("longrepr"))
    crash_message = _report_value_text(crash.get("message"))
    failure_text = "\n".join(
        text for text in (crash_message, traceback_text) if text
    )

    concise_message = crash_message
    if not concise_message:
        error_lines = [
            line.strip()[2:].strip()
            for line in traceback_text.splitlines()
            if line.strip().startswith("E ")
        ]
        concise_message = error_lines[-1] if error_lines else next(
            (line.strip() for line in traceback_text.splitlines() if line.strip()),
            "No failure message available.",
        )

    exception_match = re.search(
        r"\b([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception))\b",
        "\n".join((crash_message, traceback_text)),
    )
    location = {}
    if crash.get("path") is not None:
        location["path"] = str(crash["path"])
    if crash.get("lineno") is not None:
        location["line"] = crash["lineno"]

    classification = classify_failure_details(
        failure_text,
        test.get("nodeid", ""),
    )
    return {
        "phase": phase,
        "exception_type": exception_match.group(1) if exception_match else None,
        "message": concise_message[:1200],
        "location": location or None,
        "traceback": traceback_text[:20000] or None,
        **classification,
    }


def summarize_mutation_statuses(status_counts):
    """Calculate mutation score from mutants with a conclusive outcome only."""
    normalized = {str(status).lower(): int(count) for status, count in status_counts.items()}
    killed = normalized.get("killed", 0) + normalized.get("ok_killed", 0)
    survived = normalized.get("survived", 0) + normalized.get("bad_survived", 0)
    total = sum(normalized.values())
    scored = killed + survived
    unscored = total - scored
    return {
        "total_mutants": total,
        "killed_mutants": killed,
        "survived_mutants": survived,
        "unscored_mutants": unscored,
        "mutation_score_pct": round((killed / scored) * 100, 2) if scored else None,
    }

def parse_pytest_results():
    json_report_path = os.path.join(REPORTS_DIR, "pytest_results.json")

    if not os.path.exists(json_report_path):
        return {"error": "pytest JSON report not generated"}

    with open(json_report_path, "r") as f:
        data = json.load(f)

    summary = data.get("summary", {})
    tests   = data.get("tests", [])

    failed_tests = []
    for test in tests:
        if test.get("outcome") not in {"failed", "error"}:
            continue
        evidence = extract_failure_evidence(test)
        failed_tests.append({
            "name": test.get("nodeid", "Unknown test"),
            "outcome": test.get("outcome"),
            "message": evidence["message"],
            "failure_type": evidence["failure_type"],
            "failure_rule": evidence["rule"],
            "classification_reason": evidence["reason"],
            "evidence": evidence,
        })

    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    errors = summary.get("error", 0)
    executed = passed + failed + errors

    return {
        "total"   : summary.get("total", 0),
        "passed"  : passed,
        "failed"  : failed,
        "errors"  : errors,
        "skipped" : summary.get("skipped", 0),
        "pass_rate_pct": round(passed / executed * 100, 2) if executed else 0.0,
        "failed_tests": failed_tests,
    }

def run_mutation_testing():
    if os.path.exists(PYTEST_REPORT_FILE):
        try:
            with open(PYTEST_REPORT_FILE, "r", encoding="utf-8") as report_file:
                baseline = json.load(report_file).get("summary", {})
        except (OSError, ValueError) as exc:
            return {
                "status": "error",
                "error": f"Could not read pytest baseline report: {exc}",
                "log_file": "reports/pytest_results.json",
            }
        if baseline.get("failed", 0) or baseline.get("error", 0):
            reason = (
                "Mutation testing was skipped because the baseline test suite "
                "has failures; mutmut requires a passing baseline."
            )
            with open(os.path.join(REPORTS_DIR, "mutation.log"), "w",
                      encoding="utf-8") as log_file:
                log_file.write(reason + "\n")
            return {
                "status": "skipped",
                "reason": reason,
                "log_file": "reports/mutation.log",
            }
        if baseline.get("passed", 0) == 0:
            return {
                "status": "skipped",
                "reason": "Mutation testing was skipped because the baseline has no passing tests to evaluate.",
                "log_file": "reports/mutation.log",
            }
    else:
        return {
            "status": "error",
            "error": "Pytest baseline report is missing; mutation testing cannot verify a passing baseline.",
            "log_file": "reports/pytest_results.json",
        }

    # Create setup.cfg for mutmut to avoid CLI option errors
    setup_cfg_path = os.path.join(BASE_DIR, "setup.cfg")
    created_setup_cfg = not os.path.exists(setup_cfg_path)
    if created_setup_cfg:
        setup_cfg = "[mutmut]\npaths_to_mutate=src/\nbackup=False\nrunner=python -m pytest\ntests_dir=tests/\n"
        with open(setup_cfg_path, "w", encoding="utf-8") as config_file:
            config_file.write(setup_cfg)

    cmd = ["mutmut", "run", "--CI"]
    try:
        try:
            result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
        except FileNotFoundError:
            cmd = [sys.executable, "-m", "mutmut", "run", "--CI"]
            result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError) as exc:
        mutation_log = os.path.join(REPORTS_DIR, "mutation.log")
        with open(mutation_log, "w", encoding="utf-8") as log_file:
            log_file.write(str(exc))
        if created_setup_cfg:
            os.remove(setup_cfg_path)
        return {
            "status": "error",
            "error": f"Could not start mutation testing: {exc}",
            "log_file": "reports/mutation.log",
        }
    with open(os.path.join(REPORTS_DIR, "mutation.log"), "w", encoding="utf-8") as log_file:
        log_file.write(result.stdout)
        log_file.write(result.stderr)

    if result.returncode != 0:
        if created_setup_cfg:
            os.remove(setup_cfg_path)
        return {
            "status": "error",
            "error": f"mutmut exited with code {result.returncode}.",
            "exit_code": result.returncode,
            "log_file": "reports/mutation.log",
        }

    # Parse sqlite cache
    cache_path = os.path.join(BASE_DIR, ".mutmut-cache")
    stats_path = os.path.join(BASE_DIR, "mutants", "mutmut-stats.json")
    if not os.path.exists(cache_path):
        if os.path.exists(stats_path):
            statuses = {}
            try:
                try:
                    results = subprocess.run(
                        ["mutmut", "results"],
                        cwd=BASE_DIR,
                        capture_output=True,
                        text=True,
                    )
                except FileNotFoundError:
                    results = subprocess.run(
                        [sys.executable, "-m", "mutmut", "results"],
                        cwd=BASE_DIR,
                        capture_output=True,
                        text=True,
                    )
            except (OSError, subprocess.SubprocessError) as exc:
                results = None
                mutation_data = {
                    "status": "error",
                    "error": f"Could not read mutmut results: {exc}",
                    "log_file": "reports/mutation.log",
                }
            if results is not None and results.returncode != 0:
                mutation_data = {
                    "status": "error",
                    "error": f"mutmut results exited with code {results.returncode}.",
                    "exit_code": results.returncode,
                    "log_file": "reports/mutation.log",
                }
                results = None
            if results is not None:
                for status in re.findall(r":\s+(killed|survived|timeout|suspicious|no tests|skipped)\s*$",
                                         results.stdout, re.MULTILINE):
                    statuses[status] = statuses.get(status, 0) + 1
                counts = summarize_mutation_statuses(statuses)
                mutation_data = {
                    "status": "completed",
                    **counts,
                    "details": statuses,
                    "result_file": "mutants/mutmut-stats.json",
                }
        else:
            mutation_data = {
                "status": "error",
                "error": "Mutation cache not found",
                "exit_code": result.returncode,
                "log_file": "reports/mutation.log",
            }
    else:
        try:
            with sqlite3.connect(cache_path) as conn:
                rows = conn.execute(
                    "SELECT status, count(*) FROM mutant GROUP BY status"
                ).fetchall()

            status_counts = {status: count for status, count in rows}
            mutation_data = {
                "status": "completed",
                **summarize_mutation_statuses(status_counts),
                "details": status_counts,
            }
        except (OSError, sqlite3.Error, ValueError) as exc:
            mutation_data = {
                "status": "error",
                "error": f"Failed to parse mutmut cache: {str(exc)}",
            }

    if created_setup_cfg:
        os.remove(setup_cfg_path)
    return mutation_data

def generate_report(exit_code, pytest_data, coverage_data, mutation_data):
    print("\n[4/4] Generating structured JSON evaluation report...\n")

    mutation_score = mutation_data.get("mutation_score_pct")
    quality_score = _quality_score(
        pytest_data.get("pass_rate_pct"),
        coverage_data.get("statement_coverage_pct"),
        mutation_score,
    )
    quality_grade = _grade(
        pytest_data.get("pass_rate_pct"),
        coverage_data.get("statement_coverage_pct"),
        mutation_score,
    )

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
            "mutation_score_pct"       : mutation_score,
            "quality_score_pct"        : quality_score,
            "quality_grade"            : quality_grade,
            "grading_model": {
                "method": "equal-weight arithmetic mean",
                "weights": {
                    "pass_rate_pct": 1 / 3,
                    "statement_coverage_pct": 1 / 3,
                    "mutation_score_pct": 1 / 3,
                },
                "grade_thresholds": {
                    "A": "90-100",
                    "B": "75-89.99",
                    "C": "60-74.99",
                    "D": "below 60",
                },
            },
        }
    }

    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)

    return report

def _quality_score(pass_rate, coverage, mutation_score):
    # Treat None as 0.0 so the grade can still be calculated if mutation testing is skipped
    pass_rate = pass_rate if pass_rate is not None else 0.0
    coverage = coverage if coverage is not None else 0.0
    mutation_score = mutation_score if mutation_score is not None else 0.0
    
    metrics = (pass_rate, coverage, mutation_score)
    try:
        values = tuple(float(value) for value in metrics)
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(value) for value in values):
        return None
    return round(sum(values) / 3, 2)


def _grade(pass_rate, coverage, mutation_score):
    score = _quality_score(pass_rate, coverage, mutation_score)
    if score is None:
        return "Not graded — one or more required metrics are unavailable"
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
    needs_review = sum(1 for t in failed_tests if t.get("failure_type") == "Needs Review")
    invalid_tests = sum(1 for t in failed_tests if t.get("failure_type") == "Invalid AI Test")
    env_failures = sum(1 for t in failed_tests if t.get("failure_type") == "Environment Failure")
    real_bugs = sum(1 for t in failed_tests if t.get("failure_type") == "Real Software Bug")
    
    passed = pytest_data.get("passed", 0)
    failed = pytest_data.get("failed", 0)
    total = passed + failed + pytest_data.get("errors", 0)

    print("================================================")
    print("       AI TEST EXECUTION & EVALUATION REPORT")
    print("================================================")
    print("\nRepository:")
    print(os.path.basename(BASE_DIR)) # Fixed: Dynamic Repository Name
    
    print("\nTest Cases:")
    print(f"{pytest_data.get('total', 0)}")
    
    print("\nExecution:")
    print(f"Executed       : {pytest_data.get('total', 0)}")
    print(f"Passed         : {passed}")
    print(f"Failed         : {failed + pytest_data.get('errors', 0)}")
    
    print("\nFunctional Correctness:")
    print(f"Correct        : {passed}")
    print(f"Incorrect      : {failed + pytest_data.get('errors', 0)}")
    
    print("\nCoverage:")
    print(f"Line Coverage     : {coverage_data.get('statement_coverage_pct', 0)}%")
    print(f"Branch Coverage   : {coverage_data.get('branch_coverage_pct', 0)}%") 
    print(f"Function Coverage : {coverage_data.get('function_coverage_pct', 0)}%")
    
    mutation_total = mutation_data.get("total_mutants") if isinstance(mutation_data, dict) else None
    mutation_killed = mutation_data.get("killed_mutants", 0) if isinstance(mutation_data, dict) else 0
    mutation_survived = mutation_data.get("survived_mutants", 0) if isinstance(mutation_data, dict) else 0
    mutation_score = mutation_data.get("mutation_score_pct") if isinstance(mutation_data, dict) else None
    mutation_status = mutation_data.get("status", "error") if isinstance(mutation_data, dict) else "error"
    
    print("\nMutation Testing:")
    if mutation_status == "completed":
        print(f"Total Mutants     : {mutation_total}")
        print(f"Killed Mutants    : {mutation_killed}")
        print(f"Survived Mutants  : {mutation_survived}")
        print(f"Mutation Score    : {mutation_score}%")
    else:
        print(f"Status            : {mutation_status}")
        print(f"Reason            : {mutation_data.get('reason') or mutation_data.get('error')}")
    
    print("\nFailure Analysis:")
    print(f"Real Software Bugs      : {real_bugs}")
    print(f"Invalid AI Tests        : {invalid_tests}")
    print(f"Environment Failures    : {env_failures}")
    print(f"Needs Review            : {needs_review}")
    
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