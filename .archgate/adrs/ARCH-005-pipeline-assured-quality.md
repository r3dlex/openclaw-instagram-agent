---
id: ARCH-005
title: Pipeline-Assured Quality
status: accepted
date: 2026-03-18
domain: quality
enforced_by: pipeline:ci
---

# ARCH-005: Pipeline-Assured Quality

## Status

Accepted

## Context

Manual testing is unreliable. Architectural decisions drift over time if not enforced. Every ADR and design constraint should be verified automatically.

## Decision

- Python-based pipeline runner in `tools/pipeline_runner/`
- Each ADR references the pipeline(s) that enforce it
- Pipelines compose reusable steps: lint, test, security scan, ADR check, docs check
- Five pipelines: `ci`, `test`, `security`, `docs`, `pre-commit`
- CI pipeline runs all checks; specialized pipelines run subsets
- Pipeline results are structured (pass/fail per step with timing)

## Consequences

- **Positive:** Every ADR is backed by automated verification
- **Positive:** Consistent quality regardless of who commits
- **Positive:** Pipeline failures block bad merges
- **Negative:** Pipeline maintenance overhead
- **Negative:** False positives from secret scanning need tuning

## Enforcement

- `tests/test_pipeline.py` tests the pipeline engine itself
- Pipeline `ci` is the master gate for all commits
- See `spec/PIPELINES.md` for full pipeline documentation
