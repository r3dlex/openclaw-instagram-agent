# Testing

## Running Tests

```bash
# Via script (auto-selects Docker or Poetry)
./scripts/test.sh

# Via Poetry directly
poetry run pytest tests/ -v

# With coverage
poetry run pytest tests/ -v --cov=openclaw_instagram --cov-report=html

# Via Docker
docker compose run --rm --entrypoint pytest agent tests/ -v
```

## Running Pipelines

Pipelines are the recommended way to run tests alongside lint, security, and docs checks. See [PIPELINES.md](PIPELINES.md) for full details.

```bash
# Full CI (lint + tests + security + docs)
poetry run pipeline ci

# Tests only (lint + pytest)
poetry run pipeline test

# Security checks only
poetry run pipeline security

# Pre-commit (fast)
poetry run pipeline pre-commit
```

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures (settings, mocked clients)
├── test_config.py           # Configuration loading and validation (ARCH-003)
├── test_human_delay.py      # Delay utilities and rate limiter (ARCH-002)
├── test_agent.py            # Agent orchestration logic (ARCH-001)
├── test_telegram.py         # Telegram notifier (notifications)
├── test_pipeline.py         # Pipeline engine (ARCH-005)
└── test_pipeline_steps.py   # Pipeline step factories (ARCH-005)
```

## What Each Test File Covers

| Test file | What it tests | ADR enforced |
|-----------|-------------|--------------|
| `test_config.py` | Settings loading, account parsing, defaults | ARCH-003 |
| `test_human_delay.py` | Jitter bounds, rate limiter logic, hour pruning | ARCH-002 |
| `test_agent.py` | API-first routing, browser fallback on cooldown | ARCH-001 |
| `test_pipeline.py` | Pipeline engine: pass/fail/skip/continue, decorators | ARCH-005 |
| `test_telegram.py` | Notifier: send, no-op, engagement/cooldown/DM/error alerts | — |
| `test_pipeline_steps.py` | Step factories: env check, ADR check, docs check | ARCH-005 |

## Test Philosophy

- **Unit tests** cover config, rate limiting, delay math, orchestration, and pipeline logic
- **No live API calls** in tests; instagrapi client is mocked
- **No browser automation** in tests; Playwright calls are mocked
- **Pipeline steps** test against real project files (ADRs, .env.example, spec/)
- Integration testing against Instagram is manual (see below)

## Manual Integration Testing

For live testing (use a test account, never production):

```bash
# Check status
openclaw-instagram status

# Test engagement on a single account
INSTAGRAM_USERNAME=test_acct INSTAGRAM_PASSWORD=... \
  openclaw-instagram engage --list a
```

## Adding Tests

1. Place test files in `tests/` with `test_` prefix
2. Use fixtures from `conftest.py` for settings and mocked clients
3. Run `poetry run pipeline pre-commit` before committing
4. If adding a new ADR, add a corresponding test and reference the pipeline that enforces it
