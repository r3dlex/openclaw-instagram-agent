---
id: ARCH-001
title: API-First with Browser Fallback
status: accepted
date: 2026-03-18
domain: instagram-client
enforced_by: pipeline:ci
---

# ARCH-001: API-First with Browser Fallback

## Status

Accepted

## Context

Instagram interaction can happen via private API (instagrapi) or browser automation (Playwright). The API is faster and lower-overhead but risks rate limits and challenges. Browser automation is slower but more resilient since it mimics real user behavior.

## Decision

Use instagrapi as the primary interaction method. When the API fails due to rate limiting or challenge requirements, fall back to Playwright browser automation. Wait `API_RETRY_HOURS` (default 24h) before retrying the API.

## Consequences

- **Positive:** Fast engagement via API under normal conditions
- **Positive:** Graceful degradation to browser when API is unavailable
- **Negative:** Two codepaths to maintain (API + browser)
- **Negative:** Browser fallback is slower and more fragile

## Enforcement

- `tests/test_agent.py` validates the failover logic
- Pipeline `ci` runs these tests on every commit
- ADR compliance checked by `pipeline docs`
