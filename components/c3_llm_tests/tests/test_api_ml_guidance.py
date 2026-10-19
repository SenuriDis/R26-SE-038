"""
tests/test_api_ml_guidance.py
──────────────────────────────
The /run API (used by the integrated UI) must drive Agent 1 with
Component 2's guidance exactly like the CLI / GitHub Action path, and
fall back to the plain path when no guidance is sent.

Run with: python -m pytest tests/test_api_ml_guidance.py -v
"""

import api.main as api
from src.models.schemas import PipelineOutput


class _RecordingPipeline:
    calls = []

    def run(self, pipeline_input):
        self.calls.append(("run", pipeline_input))
        return self._output(pipeline_input.run_id)

    def run_from_ml_report(self, repository_path, enriched_segments, run_id):
        self.calls.append(("run_from_ml_report", enriched_segments))
        return self._output(run_id)

    @staticmethod
    def _output(run_id):
        return PipelineOutput(
            run_id=run_id, repository_path=".",
            segments_processed=0, segments_with_valid_tests=0,
        )


class _NoopWriter:
    def save(self, _output):
        pass


def _request(**guidance):
    return api.PipelineRequest(repository_path=".", segments=[
        api.SegmentRequest(
            function_name="risky",
            file_path="sample.py",
            source_code="def risky(value):\n    return value\n",
            risk_score=0.9,
            **guidance,
        ),
    ])


def _run(monkeypatch, request):
    _RecordingPipeline.calls = []
    monkeypatch.setattr(api, "TestingPipeline", _RecordingPipeline)
    monkeypatch.setattr(api, "OutputWriter", _NoopWriter)
    api._execute_pipeline(request, ".")
    return _RecordingPipeline.calls


def test_run_uses_c2_guidance_like_the_cli(monkeypatch):
    calls = _run(monkeypatch, _request(
        risk_level="HIGH",
        recommended_test_depth="exhaustive",
        test_types=["boundary_tests", "negative_tests"],
        explanation_text="Deep nesting.",
        top_risk_factors=[{"feature": "nesting_depth", "direction": "increases"}],
        confidence=0.8,
    ))

    assert [name for name, _ in calls] == ["run_from_ml_report"]
    enriched = calls[0][1][0]
    assert enriched.risk_level == "HIGH"
    assert enriched.test_depth == "exhaustive"
    assert enriched.min_test_cases == 10
    assert "negative_tests" in enriched.effective_test_types()
    assert enriched.explanation_text == "Deep nesting."
    assert enriched.top_risk_factors[0]["feature"] == "nesting_depth"


def test_run_falls_back_to_tier_default_depth(monkeypatch):
    calls = _run(monkeypatch, _request(risk_level="medium"))

    enriched = calls[0][1][0]
    assert enriched.risk_level == "MEDIUM"
    assert enriched.test_depth == "boundary"
    assert enriched.min_test_cases == 6


def test_run_without_guidance_keeps_the_plain_path(monkeypatch):
    calls = _run(monkeypatch, _request())

    assert [name for name, _ in calls] == ["run"]
