"""Concrete pipeline definitions.

Each function builds and returns a Pipeline ready to run.
Pipelines are registered in REGISTRY for CLI discovery.
"""

from __future__ import annotations

from tools.pipeline_runner.engine import Pipeline, Step
from tools.pipeline_runner.steps import (
    check_adrs,
    check_docs_references,
    check_env_example,
    check_no_secrets,
    run_pytest,
    run_ruff,
    run_shell,
)


def ci_pipeline() -> Pipeline:
    """Full CI pipeline: lint, test, security, docs, ADR compliance."""
    p = Pipeline("ci")
    p.add_step(Step("lint", run_ruff()))
    p.add_step(Step("unit-tests", run_pytest("tests/")))
    p.add_step(Step("env-check", check_env_example()))
    p.add_step(Step("secret-scan", check_no_secrets()))
    p.add_step(Step("adr-compliance", check_adrs()))
    p.add_step(Step("docs-integrity", check_docs_references()))
    return p


def test_pipeline() -> Pipeline:
    """Test-only pipeline: lint + tests."""
    p = Pipeline("test")
    p.add_step(Step("lint", run_ruff()))
    p.add_step(Step("unit-tests", run_pytest("tests/")))
    return p


def security_pipeline() -> Pipeline:
    """Security pipeline: env, secrets, gitignore checks."""
    p = Pipeline("security")
    p.add_step(Step("env-check", check_env_example()))
    p.add_step(Step("secret-scan", check_no_secrets()))
    gitignore_cmd = "git ls-files --cached -- .env .env.local | grep -q . && exit 1 || exit 0"
    p.add_step(Step("gitignore-check", run_shell(gitignore_cmd)))
    return p


def docs_pipeline() -> Pipeline:
    """Documentation pipeline: ADR compliance + doc integrity."""
    p = Pipeline("docs")
    p.add_step(Step("adr-compliance", check_adrs()))
    p.add_step(Step("docs-integrity", check_docs_references()))
    return p


def pre_commit_pipeline() -> Pipeline:
    """Pre-commit pipeline: fast checks before committing."""
    p = Pipeline("pre-commit")
    p.add_step(Step("lint", run_ruff()))
    p.add_step(Step("secret-scan", check_no_secrets()))
    p.add_step(Step("env-check", check_env_example()))
    return p


# Pipeline registry for CLI lookup
REGISTRY: dict[str, callable] = {
    "ci": ci_pipeline,
    "test": test_pipeline,
    "security": security_pipeline,
    "docs": docs_pipeline,
    "pre-commit": pre_commit_pipeline,
}
