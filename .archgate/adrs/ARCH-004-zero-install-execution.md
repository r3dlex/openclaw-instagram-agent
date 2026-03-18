---
id: ARCH-004
title: Zero-Install Execution
status: accepted
date: 2026-03-18
domain: deployment
enforced_by: pipeline:ci
---

# ARCH-004: Zero-Install Execution

## Status

Accepted

## Context

Contributors and the OpenClaw agent should be able to run the project without manual dependency management. The project should work on any machine with Docker or Poetry installed.

## Decision

- Docker as primary zero-install method (Dockerfile + docker-compose.yml)
- Poetry as secondary method for local development
- Shell scripts in `scripts/` auto-detect Docker or Poetry
- Pipelines run via `poetry run pipeline <name>` or within Docker
- All tools (lint, test, pipelines) are registered as Poetry scripts

## Consequences

- **Positive:** Clone, configure `.env`, run — no manual `pip install`
- **Positive:** Consistent environments across machines
- **Negative:** Docker image build takes time on first run
- **Negative:** Two execution paths (Docker / Poetry) to maintain

## Enforcement

- Dockerfile builds successfully in CI
- Pipeline `ci` validates the full tool chain works
- `scripts/run.sh` tested as the canonical entry point
