"""Pipeline execution engine.

A pipeline is a sequence of Steps. Each step is a callable that returns a StepResult.
Pipelines stop on first failure unless `continue_on_failure` is set.
"""

from __future__ import annotations

import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class StepStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    name: str
    status: StepStatus
    duration_s: float = 0.0
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    name: str
    steps: list[StepResult] = field(default_factory=list)
    duration_s: float = 0.0

    @property
    def passed(self) -> bool:
        return all(s.status != StepStatus.FAILED for s in self.steps)

    @property
    def summary(self) -> str:
        total = len(self.steps)
        passed = sum(1 for s in self.steps if s.status == StepStatus.PASSED)
        failed = sum(1 for s in self.steps if s.status == StepStatus.FAILED)
        skipped = sum(1 for s in self.steps if s.status == StepStatus.SKIPPED)
        status = "PASSED" if self.passed else "FAILED"
        return (
            f"Pipeline '{self.name}': {status} "
            f"({passed}/{total} passed, {failed} failed, {skipped} skipped) "
            f"in {self.duration_s:.2f}s"
        )


StepFn = Callable[[], StepResult | bool | None]


@dataclass
class Step:
    """A single pipeline step.

    The `fn` callable should return:
    - StepResult for full control
    - True/None for pass
    - False for failure
    - Or raise an exception for failure with traceback
    """

    name: str
    fn: StepFn
    required: bool = True


class Pipeline:
    """Declarative pipeline of sequential steps."""

    def __init__(self, name: str, continue_on_failure: bool = False) -> None:
        self.name = name
        self.continue_on_failure = continue_on_failure
        self._steps: list[Step] = []

    def step(
        self, name: str, *, required: bool = True
    ) -> Callable[[StepFn], StepFn]:
        """Decorator to register a step."""

        def decorator(fn: StepFn) -> StepFn:
            self._steps.append(Step(name=name, fn=fn, required=required))
            return fn

        return decorator

    def add_step(self, step: Step) -> None:
        self._steps.append(step)

    def run(self) -> PipelineResult:
        result = PipelineResult(name=self.name)
        pipeline_start = time.monotonic()
        has_failure = False

        logger.info("pipeline_start", pipeline=self.name, steps=len(self._steps))

        for step in self._steps:
            if has_failure and not self.continue_on_failure:
                step_result = StepResult(
                    name=step.name,
                    status=StepStatus.SKIPPED,
                    message="Skipped due to prior failure",
                )
                result.steps.append(step_result)
                logger.info("step_skipped", step=step.name)
                continue

            step_start = time.monotonic()
            try:
                raw = step.fn()
                duration = time.monotonic() - step_start

                if isinstance(raw, StepResult):
                    raw.duration_s = duration
                    step_result = raw
                elif raw is False:
                    step_result = StepResult(
                        name=step.name,
                        status=StepStatus.FAILED,
                        duration_s=duration,
                        message="Step returned False",
                    )
                else:
                    step_result = StepResult(
                        name=step.name,
                        status=StepStatus.PASSED,
                        duration_s=duration,
                    )

            except Exception as e:
                duration = time.monotonic() - step_start
                step_result = StepResult(
                    name=step.name,
                    status=StepStatus.FAILED,
                    duration_s=duration,
                    message=str(e),
                    details={"traceback": traceback.format_exc()},
                )

            result.steps.append(step_result)

            if step_result.status == StepStatus.FAILED:
                has_failure = True
                logger.error(
                    "step_failed",
                    step=step.name,
                    message=step_result.message,
                    duration=f"{step_result.duration_s:.2f}s",
                )
            else:
                logger.info(
                    "step_passed",
                    step=step.name,
                    duration=f"{step_result.duration_s:.2f}s",
                )

        result.duration_s = time.monotonic() - pipeline_start
        logger.info(
            "pipeline_done", pipeline=self.name, passed=result.passed, summary=result.summary
        )
        return result
