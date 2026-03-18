"""Tests for the pipeline runner engine and steps."""

from __future__ import annotations

from tools.pipeline_runner.engine import Pipeline, Step, StepResult, StepStatus


def test_pipeline_all_pass():
    p = Pipeline("test-all-pass")
    p.add_step(Step("step1", lambda: True))
    p.add_step(Step("step2", lambda: None))
    result = p.run()
    assert result.passed
    assert len(result.steps) == 2
    assert all(s.status == StepStatus.PASSED for s in result.steps)


def test_pipeline_stops_on_failure():
    p = Pipeline("test-stop-on-fail")
    p.add_step(Step("step1", lambda: True))
    p.add_step(Step("step2", lambda: False))
    p.add_step(Step("step3", lambda: True))
    result = p.run()
    assert not result.passed
    assert result.steps[0].status == StepStatus.PASSED
    assert result.steps[1].status == StepStatus.FAILED
    assert result.steps[2].status == StepStatus.SKIPPED


def test_pipeline_continue_on_failure():
    p = Pipeline("test-continue", continue_on_failure=True)
    p.add_step(Step("step1", lambda: False))
    p.add_step(Step("step2", lambda: True))
    result = p.run()
    assert not result.passed
    assert result.steps[0].status == StepStatus.FAILED
    assert result.steps[1].status == StepStatus.PASSED


def test_pipeline_exception_is_failure():
    def raise_error():
        raise ValueError("boom")

    p = Pipeline("test-exception")
    p.add_step(Step("step1", raise_error))
    result = p.run()
    assert not result.passed
    assert result.steps[0].status == StepStatus.FAILED
    assert "boom" in result.steps[0].message


def test_step_result_passthrough():
    def custom_step():
        return StepResult(name="custom", status=StepStatus.PASSED, message="ok")

    p = Pipeline("test-custom")
    p.add_step(Step("step1", custom_step))
    result = p.run()
    assert result.passed
    assert result.steps[0].message == "ok"


def test_pipeline_summary():
    p = Pipeline("test-summary")
    p.add_step(Step("s1", lambda: True))
    p.add_step(Step("s2", lambda: True))
    result = p.run()
    assert "PASSED" in result.summary
    assert "2/2 passed" in result.summary


def test_pipeline_decorator():
    p = Pipeline("test-decorator")

    @p.step("decorated-step")
    def my_step():
        return True

    result = p.run()
    assert result.passed
    assert result.steps[0].name == "decorated-step"


def test_step_duration_recorded():
    p = Pipeline("test-duration")
    p.add_step(Step("step1", lambda: True))
    result = p.run()
    assert result.steps[0].duration_s >= 0
    assert result.duration_s >= 0
