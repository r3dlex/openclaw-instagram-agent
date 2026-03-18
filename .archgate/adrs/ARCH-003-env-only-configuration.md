---
id: ARCH-003
title: Environment-Only Configuration
status: accepted
date: 2026-03-18
domain: configuration
enforced_by: pipeline:security
---

# ARCH-003: Environment-Only Configuration

## Status

Accepted

## Context

Credentials, account lists, and operational parameters must be configurable without touching code. Hardcoded values risk leaking secrets to git. The repo must be public-safe at all times.

## Decision

- All configuration via environment variables loaded from `.env`
- `.env` is gitignored; `.env.example` provides dummy templates
- Pydantic Settings validates and types all config at startup
- No credentials, usernames, or tokens in any tracked file
- Pipeline `security` scans for secret patterns before every commit

## Consequences

- **Positive:** Repo is always public-safe
- **Positive:** Configuration is 12-factor compliant
- **Positive:** Pydantic catches misconfigurations early
- **Negative:** Requires copying `.env.example` on fresh clone

## Enforcement

- `tests/test_config.py` validates settings loading and parsing
- Pipeline `security` checks `.env.example` exists, `.env` is gitignored, and no secrets in tracked files
- ADR compliance checked by `pipeline docs`
