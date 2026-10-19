from types import SimpleNamespace

from pipeline import run_pipeline


def test_adapt_c1_response_builds_c2_metrics(tmp_path):
    source = "def risky(value):\n    if value:\n        return len(value)\n    return 0\n"
    (tmp_path / "sample.py").write_text(source, encoding="utf-8")
    c1_response = [{
        "file": "/workspace/sample.py",
        "functions": {
            "function_names": ["risky"],
            "function_complexity": {"risky": 2},
        },
        "dependencies": {
            "function_dependencies": {"risky": ["len"]},
        },
    }]

    payload, sources, definitions = run_pipeline.adapt_c1_response(
        c1_response, tmp_path, "/workspace", "sample"
    )

    function = payload["functions"][0]
    assert function["function_name"] == "risky"
    assert function["file_path"] == "sample.py"
    assert function["start_line"] == 1
    assert function["end_line"] == 4
    assert function["cyclomatic_complexity"] == 2
    assert function["num_parameters"] == 1
    assert function["num_conditionals"] == 1
    assert function["dependencies"] == ["len"]
    assert sources["sample.py"] == source
    assert "sample.py:1" in definitions


def test_adapt_c1_payload_uses_browser_handoff_sources():
    source = "def risky(value):\n    if value:\n        return len(value)\n    return 0\n"
    c1_response = {
        "files": [{
            "file": "src/sample.py",
            "functions": {
                "function_names": ["risky"],
                "function_complexity": {"risky": 2},
            },
            "dependencies": {
                "function_dependencies": {"risky": ["len"]},
            },
        }]
    }

    payload, sources, definitions = run_pipeline.adapt_c1_payload(
        c1_response, {"src/sample.py": source}, "sample"
    )

    assert payload["functions"][0]["file_path"] == "src/sample.py"
    assert sources["src/sample.py"] == source
    assert "src/sample.py:1" in definitions


def test_build_c3_and_c4_payloads_handoff_selected_functions_and_test_code():
    source = "def risky(value):\n    if value:\n        return len(value)\n    return 0\n"
    c1_response = [{
        "file": "sample.py",
        "functions": {
            "function_names": ["risky"],
            "function_complexity": {"risky": 2},
        },
    }]
    _, sources, definitions = run_pipeline.adapt_c1_payload(
        c1_response, {"sample.py": source}, "sample"
    )
    c3_payload = run_pipeline.build_c3_payload(
        {"ranked_functions": [{
            "function_name": "risky",
            "file_path": "sample.py",
            "start_line": 1,
            "risk_score": 0.9,
            "risk_level": "HIGH",
        }]},
        sources,
        definitions,
        "sample",
    )

    assert c3_payload["segments"][0]["source_code"] == source.rstrip()
    c4_payload = run_pipeline.build_c4_payload(
        {"sample.py": source},
        {"tests": [{
            "function_name": "risky",
            "test_code": "def test_risky():\n    assert True\n",
        }]},
    )
    assert c4_payload["source_files"]["sample.py"] == source
    assert c4_payload["test_files"]["test_risky_1.py"].startswith("def test_risky")


def test_build_c3_payload_forwards_c2_guidance():
    source = "def risky(value):\n    if value:\n        return len(value)\n    return 0\n"
    _, sources, definitions = run_pipeline.adapt_c1_payload(
        [{"file": "sample.py", "functions": {"function_names": ["risky"]}}],
        {"sample.py": source},
        "sample",
    )
    factors = [{"feature": "nesting_depth", "direction": "increases"}]
    c3_payload = run_pipeline.build_c3_payload(
        {"ranked_functions": [{
            "function_name": "risky",
            "file_path": "sample.py",
            "start_line": 1,
            "risk_score": 0.9,
            "risk_level": "HIGH",
            "recommended_test_depth": "exhaustive",
            "test_types": ["boundary_tests", "negative_tests"],
            "explanation_text": "Deep nesting.",
            "top_risk_factors": factors,
            "confidence": 0.8,
        }]},
        sources,
        definitions,
        "sample",
    )

    segment = c3_payload["segments"][0]
    assert segment["risk_level"] == "HIGH"
    assert segment["recommended_test_depth"] == "exhaustive"
    assert segment["test_types"] == ["boundary_tests", "negative_tests"]
    assert segment["explanation_text"] == "Deep nesting."
    assert segment["top_risk_factors"] == factors
    assert segment["confidence"] == 0.8


def test_run_hands_off_data_through_all_component_apis(tmp_path, monkeypatch):
    target = tmp_path / "project"
    target.mkdir()
    (target / "sample.py").write_text(
        "def risky(value):\n    if value:\n        return len(value)\n    return 0\n",
        encoding="utf-8",
    )
    responses = {
        "http://c1/analyze-folder": [{
            "file": "/workspace/project/sample.py",
            "functions": {
                "function_names": ["risky"],
                "function_complexity": {"risky": 2},
            },
            "dependencies": {"function_dependencies": {"risky": ["len"]}},
        }],
        "http://c2/predict": {
            "ranked_functions": [{
                "function_name": "risky",
                "file_path": "sample.py",
                "start_line": 1,
                "end_line": 4,
                "risk_score": 0.9,
                "risk_level": "HIGH",
                "priority_rank": 1,
            }],
        },
        "http://c3/run": {
            "tests": [{
                "function_name": "risky",
                "test_code": "from sample import risky\n\ndef test_risky():\n    assert risky('x') == 1\n",
            }],
        },
        "http://c4/api/evaluate": {
            "grade": "B",
            "quality_grade": "B — Good",
            "execution_status": "PASS",
            "test_results": {"total": 1, "passed": 1},
        },
    }
    calls = []

    def fake_post_json(url, payload, timeout):
        calls.append((url, payload, timeout))
        return responses[url]

    monkeypatch.setattr(run_pipeline, "post_json", fake_post_json)
    args = SimpleNamespace(
        target=str(target),
        container_target="/workspace/project",
        c1_url="http://c1",
        c2_url="http://c2",
        c3_url="http://c3",
        c4_url="http://c4",
        min_risk_level="MEDIUM",
        max_functions=None,
        request_timeout=30,
        output=None,
    )

    result = run_pipeline.run(args)

    assert [call[0] for call in calls] == list(responses)
    assert calls[1][1]["functions"][0]["function_name"] == "risky"
    assert calls[2][1]["segments"][0]["source_code"].startswith("def risky")
    assert calls[3][1]["source_files"] == {
        "sample.py": (target / "sample.py").read_text(encoding="utf-8")
    }
    assert calls[3][1]["test_files"]["test_risky_1.py"].startswith("from sample")
    assert result["c4"]["grade"] == "B"
