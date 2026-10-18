import pytest
from fastapi import HTTPException

from pipeline import api
from pipeline.run_pipeline import PipelineError


def test_run_full_pipeline_returns_c4_result(tmp_path, monkeypatch):
    target = tmp_path / "project"
    target.mkdir()
    monkeypatch.setattr(api, "WORKSPACE_ROOT", tmp_path)
    captured = {}

    def fake_run(args):
        captured["args"] = args
        return {"c4": {"grade": "A", "test_results": {"passed": 2}}}

    monkeypatch.setattr(api.run_pipeline, "run", fake_run)

    result = api.run_full_pipeline(
        api.PipelineRequest(target_folder="project", max_functions=3)
    )

    assert result == {"grade": "A", "test_results": {"passed": 2}}
    assert captured["args"].target == str(target)
    assert captured["args"].container_target == "/workspace/project"
    assert captured["args"].max_functions == 3
    assert captured["args"].c1_url == "http://localhost:8001"


def test_run_full_pipeline_rejects_target_outside_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "WORKSPACE_ROOT", tmp_path / "workspace")
    (tmp_path / "workspace").mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    with pytest.raises(HTTPException) as error:
        api.run_full_pipeline(api.PipelineRequest(target_folder=str(outside)))

    assert error.value.status_code == 422


def test_run_full_pipeline_returns_upstream_error(tmp_path, monkeypatch):
    target = tmp_path / "project"
    target.mkdir()
    monkeypatch.setattr(api, "WORKSPACE_ROOT", tmp_path)

    def fail_run(_args):
        raise PipelineError("C2 returned HTTP 503")

    monkeypatch.setattr(api.run_pipeline, "run", fail_run)

    with pytest.raises(HTTPException) as error:
        api.run_full_pipeline(api.PipelineRequest(target_folder="project"))

    assert error.value.status_code == 502
    assert error.value.detail == "C2 returned HTTP 503"


def test_run_full_pipeline_rejects_c4_result_without_grade(tmp_path, monkeypatch):
    target = tmp_path / "project"
    target.mkdir()
    monkeypatch.setattr(api, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(api.run_pipeline, "run", lambda _args: {"c4": {"test_results": {}}})

    with pytest.raises(HTTPException) as error:
        api.run_full_pipeline(api.PipelineRequest(target_folder="project"))

    assert error.value.status_code == 502
    assert "quality grade" in error.value.detail


def test_wizard_stages_handoff_c1_to_c2_to_c3_to_c4(monkeypatch):
    source = "def risky(value):\n    if value:\n        return len(value)\n    return 0\n"
    request_c1 = api.WizardC1Request(
        c1_response={
            "files": [{
                "file": "sample.py",
                "functions": {
                    "function_names": ["risky"],
                    "function_complexity": {"risky": 2},
                },
            }]
        },
        source_files={"sample.py": source},
        project_name="sample",
    )
    calls = []

    def fake_post_json(url, payload, _timeout):
        calls.append((url, payload))
        if url.endswith("/predict"):
            return {"ranked_functions": [{
                "function_name": "risky",
                "file_path": "sample.py",
                "start_line": 1,
                "risk_score": 0.9,
                "risk_level": "HIGH",
                "priority_rank": 1,
            }]}
        if url.endswith("/run"):
            return {"tests": [{
                "function_name": "risky",
                "test_code": "def test_risky():\n    assert True\n",
            }]}
        return {"grade": "A", "test_results": {"total": 1, "passed": 1}}

    monkeypatch.setattr(api.run_pipeline, "post_json", fake_post_json)
    c2_response = api.wizard_run_c2(request_c1)
    c3_response = api.wizard_run_c3(api.WizardC3Request(
        **request_c1.model_dump(),
        c2_response=c2_response,
    ))
    c4_response = api.wizard_run_c4(api.WizardC4Request(
        source_files=request_c1.source_files,
        c3_response=c3_response,
    ))

    assert [url.rsplit("/", 1)[-1] for url, _ in calls] == ["predict", "run", "evaluate"]
    assert calls[1][1]["segments"][0]["source_code"] == source.rstrip()
    assert calls[1][1]["source_files"] == request_c1.source_files
    assert calls[2][1]["test_files"]["test_risky_1.py"].startswith("def test_risky")
    assert c4_response["grade"] == "A"


def test_wizard_rejects_unsafe_source_path():
    for unsafe_path in ("../escape.py", "C:\\escape.py"):
        with pytest.raises(HTTPException) as error:
            api._validate_wizard_source_files({unsafe_path: "def f(): pass"})
        assert error.value.status_code == 422
