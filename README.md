<p align="center">
  <img src="assets/logo.svg" alt="Instagram Agent logo" width="96" height="96">
</p>

# OpenClaw Instagram Agent

[![CI](https://github.com/r3dlex/openclaw-instagram-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/r3dlex/openclaw-instagram-agent/actions/workflows/ci.yml)

An autonomous Instagram engagement agent powered by [OpenClaw](https://docs.openclaw.ai/). Likes posts and reels from configured target accounts, monitors DMs, and reports back through your preferred messaging channel.

## Features

- **API-first engagement** via [instagrapi](https://github.com/subzeroid/instagrapi) with automatic browser fallback
- **Human-like behavior** — Gaussian-jittered delays, configurable rate limits, session persistence
- **2FA support** — Automatic TOTP code generation for accounts with two-factor authentication
- **Zero-install** — Run via Docker or Poetry, no manual dependency setup
- **Autonomous but safe** — Likes and monitors autonomously; all text replies require human approval
- **Pipeline-assured quality** — Python CI pipelines enforce architecture decisions (ADRs)
- **Inter-agent messaging** — Discovers and communicates with peer agents via [IAMQ](https://github.com/r3dlex/openclaw-inter-agent-message-queue)
- **Structured logging** — Console + JSON file output to `logs/`
- **OpenClaw native** — Integrates with heartbeats, memory, and multi-channel messaging

## Quick Start

### 1. Configure

```bash
cp .env.example .env
# Edit .env with your Instagram credentials and target accounts
```

### 2. Run

**Via Docker (recommended):**
```bash
docker compose run --rm agent status
docker compose run --rm agent engage --list a
docker compose run --rm agent dms --list a
```

**Via Poetry:**
```bash
poetry install
poetry run openclaw-instagram status
```

**Via helper script (auto-detects Docker or Poetry):**
```bash
./scripts/run.sh status
./scripts/run.sh engage --list a
```

### 3. Scheduled Engagement

```bash
# Start the cron-like engagement loop (every 4 hours)
docker compose --profile cron up -d engage-cron
```

## Architecture

```
API Client (instagrapi) ──► Rate Limiter ──► Instagram
       │                                         ▲
       │ on rate limit / challenge                │
       ▼                                          │
Browser Fallback (Playwright) ────────────────────┘
       │
       │ 24h cooldown, then retry API
```

The agent tries the API first. If Instagram rate-limits or challenges the account, it falls back to browser automation and waits 24 hours before retrying the API.

Architecture decisions are documented as [ADRs](.archgate/adrs/) and enforced by [pipelines](spec/PIPELINES.md). See [spec/ARCHITECTURE.md](spec/ARCHITECTURE.md) for full details.

## Configuration

All configuration via environment variables. See [.env.example](.env.example) for all options.

| Variable | Default | Purpose |
|----------|---------|---------|
| `INSTAGRAM_USERNAME` | — | Login username |
| `INSTAGRAM_PASSWORD` | — | Login password |
| `IG_2FA_SEED` | — | TOTP seed for auto 2FA (optional) |
| `TARGET_ACCOUNTS_A` | — | Comma-separated engagement targets |
| `MAX_ACTIONS_PER_HOUR` | 20 | Self-imposed rate limit |
| `MIN_ACTION_DELAY_SECONDS` | 10 | Minimum delay between actions |
| `MAX_ACTION_DELAY_SECONDS` | 30 | Maximum delay between actions |
| `API_RETRY_HOURS` | 24 | Hours to wait before retrying API |
| `LOG_LEVEL` | INFO | Logging level |
| `LOG_DIR` | ./logs | JSON log file directory |
| `IAMQ_ENABLED` | false | Enable inter-agent message queue |
| `IAMQ_HTTP_URL` | http://127.0.0.1:18790 | IAMQ service URL |
| `IAMQ_AGENT_ID` | instagram_agent | This agent's ID in the queue |

## Pipelines

Quality is enforced through Python pipelines. See [spec/PIPELINES.md](spec/PIPELINES.md) for full documentation.

```bash
poetry run pipeline ci          # Full CI: lint + test + security + docs + ADR compliance
poetry run pipeline test        # Lint + tests only
poetry run pipeline security    # Secret scan + env checks
poetry run pipeline pre-commit  # Fast pre-commit checks
poetry run pipeline --list      # Show all available pipelines
```

## OpenClaw Integration

This agent uses the [OpenClaw](https://docs.openclaw.ai/) workspace template:

| File | Purpose |
|------|---------|
| `AGENTS.md` | Agent workspace instructions |
| `SOUL.md` | Identity, engagement rules, contact lists |
| `BOOT.md` | Startup tasks (IAMQ registration, session check) |
| `CONFIG.md` | Runtime configuration reference |
| `HEARTBEAT.md` | Periodic task definitions |
| `TOOLS.md` | Environment-specific notes |

## Development

```bash
# Install dev dependencies
poetry install --with dev

# Run full CI pipeline
poetry run pipeline ci

# Run tests only
poetry run pytest tests/ -v

# Lint
poetry run ruff check src/ tests/ tools/
```

See [CLAUDE.md](CLAUDE.md) for development guide, [spec/TESTING.md](spec/TESTING.md) for test details, and [spec/PIPELINES.md](spec/PIPELINES.md) for pipeline documentation.

## Documentation

- [spec/ARCHITECTURE.md](spec/ARCHITECTURE.md) — System design, ADR index, data flow
- [spec/PIPELINES.md](spec/PIPELINES.md) — Pipeline definitions, ADR enforcement mapping
- [spec/TESTING.md](spec/TESTING.md) — Testing guide and test structure
- [spec/TROUBLESHOOTING.md](spec/TROUBLESHOOTING.md) — Common issues and fixes
- [spec/LEARNINGS.md](spec/LEARNINGS.md) — Runtime learnings (agent-maintained)
- [.archgate/adrs/](.archgate/adrs/) — Architecture Decision Records

## License

[MIT](LICENSE)
