# CLAUDE.md - Development Guide

## What is this repo?

An autonomous Instagram engagement agent powered by [OpenClaw](https://docs.openclaw.ai/). It likes posts/reels from configured target accounts, monitors DMs, and reports back through messaging channels.

## Quick Start

```bash
cp .env.example .env        # Fill in credentials
poetry install               # Install deps
poetry run pipeline ci       # Run full CI pipeline
./scripts/run.sh status      # Docker or Poetry auto-detected
```

## Repository Layout

```
├── CLAUDE.md               ← You are here (for dev agents: Claude, Copilot, etc.)
├── AGENTS.md               ← For the OpenClaw runtime agent
├── SOUL.md                 ← Agent personality and engagement rules
├── CONFIG.md               ← Agent runtime config (reads from .env)
├── HEARTBEAT.md            ← Periodic task config for OpenClaw heartbeats
├── TOOLS.md                ← Agent tool/environment notes
├── src/openclaw_instagram/ ← Python package
│   ├── api/client.py       ← instagrapi-based Instagram client
│   ├── browser/fallback.py ← Playwright browser fallback
│   ├── agent.py            ← Orchestrator (API → browser failover)
│   ├── config.py           ← Pydantic settings from .env
│   ├── cli.py              ← CLI entry point
│   └── utils/              ← Delays, rate limiting, logging, Telegram
├── tools/pipeline_runner/  ← Python CI pipelines
│   ├── engine.py           ← Pipeline/Step execution engine
│   ├── steps.py            ← Reusable step factories
│   ├── pipelines.py        ← Concrete pipeline definitions
│   └── cli.py              ← `poetry run pipeline <name>`
├── .archgate/adrs/         ← Architecture Decision Records
├── tests/                  ← pytest suite
├── spec/                   ← Deep documentation
│   ├── ARCHITECTURE.md     ← System design, ADR index
│   ├── PIPELINES.md        ← Pipeline docs, ADR↔pipeline mapping
│   ├── TESTING.md          ← How to run and write tests
│   ├── TROUBLESHOOTING.md  ← Common issues and fixes
│   └── LEARNINGS.md        ← Runtime learnings (agent-maintained)
├── logs/                   ← JSON log files (gitignored, .gitkeep tracked)
├── scripts/                ← Zero-install shell scripts
├── Dockerfile              ← Container build
├── docker-compose.yml      ← Service definitions
└── pyproject.toml          ← Poetry package config
```

## Two Audiences

| File | Audience | Purpose |
|------|----------|---------|
| `CLAUDE.md` | Dev agents (you) | How to develop, test, and improve the codebase |
| `AGENTS.md` | OpenClaw agent | How to operate at runtime (engage, monitor, report) |
| `SOUL.md` | OpenClaw agent | Identity, rules, contact lists |
| `CONFIG.md` | OpenClaw agent | Runtime configuration references |
| `spec/*` | Both | Deep docs, architecture, pipelines, troubleshooting |
| `.archgate/adrs/*` | Both | Architecture Decision Records |

**Do not mix concerns.** Dev changes go through git. Agent runtime state goes in `memory/`, `session_cache/`, and `.openclaw/` (all gitignored).

## Development Workflow

1. Read `spec/ARCHITECTURE.md` for system design and ADR index
2. Source code is in `src/openclaw_instagram/`
3. Add tests in `tests/` — see `spec/TESTING.md`
4. Run `poetry run pipeline pre-commit` before committing
5. Run `poetry run pipeline ci` for full validation

### Key design decisions

All decisions are documented as ADRs in `.archgate/adrs/`. Key ones:

- **ARCH-001**: instagrapi API-first, Playwright browser fallback
- **ARCH-002**: Gaussian-jittered delays, rolling-hour rate limiter
- **ARCH-003**: All config via `.env`, no hardcoded secrets
- **ARCH-004**: Zero-install via Docker or Poetry
- **ARCH-005**: Pipeline-assured quality, every ADR enforced by a pipeline
- **ARCH-006**: Human approval required for all text output

### Pipelines

Run `poetry run pipeline --list` to see available pipelines, or see `spec/PIPELINES.md` for full documentation.

```bash
poetry run pipeline ci          # Full CI: lint + test + security + docs
poetry run pipeline test        # Lint + tests only
poetry run pipeline security    # Secret scan + env checks
poetry run pipeline docs        # ADR + docs integrity
poetry run pipeline pre-commit  # Fast pre-commit checks
```

### Sensitive files (gitignored)

- `.env` — credentials and config
- `.openclaw/` — agent state
- `memory/` — agent memory files
- `USER.md` — personal user info
- `IDENTITY.md` — agent identity (filled at runtime)
- `session_cache/` — Instagram session cookies
- `logs/*.log` — Runtime log files (only `.gitkeep` is tracked)

## Spec (progressive disclosure)

For deeper documentation, see `spec/`:
- `spec/ARCHITECTURE.md` — System design, ADR index, component details
- `spec/PIPELINES.md` — Pipeline definitions, ADR↔pipeline mapping, step guide
- `spec/TESTING.md` — Test philosophy, structure, how to run/add tests
- `spec/TROUBLESHOOTING.md` — Common issues and resolutions
- `spec/LEARNINGS.md` — Runtime learnings maintained by the agent
