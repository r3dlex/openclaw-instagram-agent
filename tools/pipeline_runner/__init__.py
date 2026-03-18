"""Pipeline runner: declarative CI/CD-style pipelines in Python.

Zero-install: runs via `poetry run pipeline <name>` or `docker compose run agent pipeline <name>`.
"""

from tools.pipeline_runner.engine import Pipeline, PipelineResult, Step

__all__ = ["Pipeline", "PipelineResult", "Step"]
