"""Tests for pipeline step factories."""

from __future__ import annotations

from tools.pipeline_runner.engine import StepStatus
from tools.pipeline_runner.steps import check_adrs, check_docs_references, check_env_example


def test_check_env_example_passes():
    """Should pass since .env.example exists and .gitignore has .env."""
    step = check_env_example()
    result = step()
    assert result.status == StepStatus.PASSED


def test_check_adrs_passes():
    """Should pass since ADR files exist with valid structure."""
    step = check_adrs()
    result = step()
    assert result.status == StepStatus.PASSED
    assert result.details["adr_count"] >= 1


def test_check_docs_references_passes():
    """Should pass since all required spec/ docs exist."""
    step = check_docs_references()
    result = step()
    assert result.status == StepStatus.PASSED
