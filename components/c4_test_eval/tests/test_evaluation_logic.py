import json
import sqlite3
import subprocess

import execute_tests
import run as docker_runner


def test_assertion_mismatch_requires_review():
    assert execute_tests.classify_failure(
        "AssertionError: assert -1900 == 80.0"
    ) == "Needs Review"


def test_syntax_error_in_generated_test_is_invalid_ai_test():
    traceback = 'SyntaxError: invalid syntax in "tests/test_generated_case.py"'
    assert execute_tests.classify_failure(traceback) == "Invalid AI Test"
    assert execute_tests.classify_failure_details(traceback)["rule"] == (
        "generated_test_syntax_error"
    )


def test_missing_test_dependency_is_classified_as_environment_failure():
    details = execute_tests.classify_failure_details(
        "ModuleNotFoundError: No module named 'pytest_cov'"
    )

    assert details["failure_type"] == "Environment Failure"
    assert details["rule"] == "known_environment_error"


def test_mutation_score_excludes_inconclusive_mutants():
    result = execute_tests.summarize_mutation_statuses({
        "killed": 15,
        "survived": 5,
        "timeout": 2,
        "suspicious": 1,
    })

    assert result == {
        "total_mutants": 23,
        "killed_mutants": 15,
        "survived_mutants": 5,
        "unscored_mutants": 3,
        "mutation_score_pct": 75.0,
    }


def test_mutation_score_is_unavailable_when_no_mutants_were_scored():
    result = execute_tests.summarize_mutation_statuses({"timeout": 2, "skipped": 1})

    assert result["mutation_score_pct"] is None
    assert result["unscored_mutants"] == 3


def test_pytest_pass_rate_excludes_skipped_and_skips_are_not_failures(tmp_path, monkeypatch):
    report_path = tmp_path / "pytest_results.json"
    report_path.write_text(json.dumps({
        "summary": {"total": 3, "passed": 1, "failed": 1, "error": 0, "skipped": 1},
        "tests": [
            {
                "nodeid": "tests/test_generated.py::test_expected_value",
                "outcome": "failed",
                "call": {"longrepr": "AssertionError: assert 1 == 2"},
            },
            {"nodeid": "tests/test_generated.py::test_skipped", "outcome": "skipped"},
        ],
    }), encoding="utf-8")
    monkeypatch.setattr(execute_tests, "REPORTS_DIR", str(tmp_path))

    result = execute_tests.parse_pytest_results()

    assert result["total"] == 3
    assert result["passed"] == 1
    assert result["failed"] == 1
    assert result["skipped"] == 1
    assert result["pass_rate_pct"] == 50.0
    assert len(result["failed_tests"]) == 1
    assert result["failed_tests"][0]["failure_type"] == "Needs Review"


def test_failure_report_preserves_structured_location_and_traceback(
    tmp_path, monkeypatch
):
    traceback = (
        "Traceback (most recent call last):\n"
        "  File \"tests/test_generated.py\", line 17, in test_expected_value\n"
        f"E   AssertionError: {'unexpected value ' * 40}\n"
    )
    report_path = tmp_path / "pytest_results.json"
    report_path.write_text(json.dumps({
        "summary": {"total": 1, "passed": 0, "failed": 1, "error": 0},
        "tests": [{
            "nodeid": "tests/test_generated.py::test_expected_value",
            "outcome": "failed",
            "call": {
                "outcome": "failed",
                "crash": {
                    "path": "tests/test_generated.py",
                    "lineno": 17,
                    "message": "AssertionError: expected value did not match",
                },
                "longrepr": traceback,
            },
        }],
    }), encoding="utf-8")
    monkeypatch.setattr(execute_tests, "REPORTS_DIR", str(tmp_path))

    result = execute_tests.parse_pytest_results()
    failure = result["failed_tests"][0]

    assert failure["failure_type"] == "Needs Review"
    assert failure["failure_rule"] == "assertion_mismatch"
    assert failure["evidence"]["phase"] == "call"
    assert failure["evidence"]["exception_type"] == "AssertionError"
    assert failure["evidence"]["location"] == {
        "path": "tests/test_generated.py",
        "line": 17,
    }
    assert len(failure["evidence"]["traceback"]) > 300
    assert "expected value did not match" in failure["message"]


def test_quality_grade_uses_equal_weights_and_requires_all_metrics():
    assert execute_tests._quality_score(90, 80, 70) == 80
    assert execute_tests._grade(90, 80, 70) == "B — Good"
    assert execute_tests._quality_score(90, 80, None) is None
    assert execute_tests._grade(90, 80, None).startswith("Not graded")


def test_evaluation_report_exposes_score_and_grading_model(tmp_path, monkeypatch):
    report_path = tmp_path / "evaluation_report.json"
    monkeypatch.setattr(execute_tests, "REPORT_FILE", str(report_path))

    report = execute_tests.generate_report(
        0,
        {"pass_rate_pct": 90},
        {"statement_coverage_pct": 80},
        {"status": "completed", "mutation_score_pct": 70},
    )

    assert report["evaluation_summary"]["quality_score_pct"] == 80
    assert report["evaluation_summary"]["quality_grade"] == "B — Good"
    assert report["evaluation_summary"]["grading_model"]["method"] == (
        "equal-weight arithmetic mean"
    )
    assert json.loads(report_path.read_text(encoding="utf-8")) == report


def test_docker_orchestrator_applies_isolation_controls(tmp_path):
    command = docker_runner.docker_run_command("test-eval-unit", str(tmp_path))

    assert command[command.index("--network") + 1] == "none"
    assert command[command.index("--cap-drop") + 1] == "ALL"
    assert command[command.index("--security-opt") + 1] == "no-new-privileges"
    assert command[command.index("--pids-limit") + 1] == "256"
    assert command[command.index("--memory") + 1] == "2g"
    assert command[command.index("--cpus") + 1] == "2"
    assert command[command.index("--volume") + 1].endswith(":/app/reports")


def test_mutation_testing_skips_when_baseline_failed(tmp_path, monkeypatch):
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    baseline_path = report_dir / "pytest_results.json"
    baseline_path.write_text(json.dumps({
        "summary": {"passed": 1, "failed": 1, "error": 0},
    }), encoding="utf-8")
    monkeypatch.setattr(execute_tests, "PYTEST_REPORT_FILE", str(baseline_path))
    monkeypatch.setattr(execute_tests, "REPORTS_DIR", str(report_dir))

    result = execute_tests.run_mutation_testing()

    assert result["status"] == "skipped"
    assert "baseline test suite has failures" in result["reason"]
    assert (report_dir / "mutation.log").exists()


def test_mutation_testing_accepts_surviving_mutants_as_a_completed_run(
    tmp_path, monkeypatch
):
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    baseline_path = report_dir / "pytest_results.json"
    baseline_path.write_text(json.dumps({
        "summary": {"passed": 1, "failed": 0, "error": 0},
    }), encoding="utf-8")
    monkeypatch.setattr(execute_tests, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(execute_tests, "REPORTS_DIR", str(report_dir))
    monkeypatch.setattr(execute_tests, "PYTEST_REPORT_FILE", str(baseline_path))

    def run_mutmut(command, **kwargs):
        assert command == ["mutmut", "run", "--CI"]
        with sqlite3.connect(tmp_path / ".mutmut-cache") as connection:
            connection.execute("CREATE TABLE mutant (status TEXT)")
            connection.executemany(
                "INSERT INTO mutant (status) VALUES (?)",
                [("killed",), ("survived",), ("timeout",)],
            )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(execute_tests.subprocess, "run", run_mutmut)

    result = execute_tests.run_mutation_testing()

    assert result["status"] == "completed"
    assert result["killed_mutants"] == 1
    assert result["survived_mutants"] == 1
    assert result["unscored_mutants"] == 1
    assert result["mutation_score_pct"] == 50.0
