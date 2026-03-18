---
id: ARCH-002
title: Human-Like Rate Limiting
status: accepted
date: 2026-03-18
domain: safety
enforced_by: pipeline:ci
---

# ARCH-002: Human-Like Rate Limiting

## Status

Accepted

## Context

Instagram detects and bans automated behavior. Simple fixed delays between actions are easily fingerprinted. We need realistic, non-deterministic timing.

## Decision

- Use Gaussian-jittered delays between all actions (not fixed intervals)
- Enforce a configurable maximum actions per rolling hour (`MAX_ACTIONS_PER_HOUR`)
- Minimum and maximum delay bounds are configurable via environment variables
- The RateLimiter tracks action timestamps and blocks when the hourly cap is reached

## Consequences

- **Positive:** Harder for Instagram to detect automation
- **Positive:** Self-imposed limits prevent accidental spam
- **Negative:** Slower throughput than fixed-delay approaches
- **Negative:** Engagement cycles take longer to complete

## Enforcement

- `tests/test_human_delay.py` validates jitter bounds and rate limiter logic
- `tests/test_agent.py` validates rate limiting is applied in the orchestrator
- Pipeline `ci` runs these tests on every commit
