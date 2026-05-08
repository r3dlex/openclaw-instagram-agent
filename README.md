<p align="center">
  <img src="assets/banner.svg" alt="openclaw-instagram-agent" width="600">
</p>

# OpenClaw Instagram Agent

[![CI](https://github.com/r3dlex/openclaw-instagram-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/r3dlex/openclaw-instagram-agent/actions/workflows/ci.yml)

An autonomous Instagram engagement agent powered by [OpenClaw](https://docs.openclaw.ai/) (also known as InstaOps). Likes posts and reels from configured target accounts, monitors DMs, and reports back through your preferred messaging channel.

## Features

- **API-first engagement** via [instagrapi](https://github.com/subzeroid/instagrapi) with automatic browser fallback
- **Human-like behavior** — Gaussian-jittered delays, configurable rate limits, session persistence
- **2FA support** — automatic TOTP code generation for accounts with two-factor authentication
- **Autonomous but safe** — likes and monitors autonomously; all text replies require human approval
- **Pipeline-assured quality** — Python CI pipelines enforce architecture decisions (ADRs)
- **Inter-agent messaging** — discovers and communicates with peer agents via IAMQ
- **Zero-install** — run via Docker or Poetry, no manual dependency setup

## Skills

| Skill | Description |
|-------|-------------|
| `engagement_analyze` | Analyze engagement metrics for recent Instagram posts over a configurable lookback period |

Workspace skills also available: `iamq_message_send`, `log_learning`, `improve_skill`

Skills auto-improve via post-execution hooks and nightly batch review.

## Architecture

- **Language**: Python
- **IAMQ ID**: `instagram_agent`
- **Runtime**: Docker

```
API Client (instagrapi) ──► Rate Limiter ──► Instagram
       │                                         ▲
       │ on rate limit / challenge                │
       ▼                                          │
Browser Fallback (Playwright) ────────────────────┘
```

The agent tries the API first. On rate-limit or challenge it falls back to browser automation and waits 24 hours before retrying the API.

### Docker Volume Mounts

```yaml
- ../skills-cli:/skills-cli:ro
- ../skills:/workspace/skills:rw
- ./skills:/agent/skills:rw
```

### Key Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `INSTAGRAM_USERNAME` | — | Login username |
| `INSTAGRAM_PASSWORD` | — | Login password |
| `IG_2FA_SEED` | — | TOTP seed for auto 2FA (optional) |
| `TARGET_ACCOUNTS_A` | — | Comma-separated engagement targets |
| `MAX_ACTIONS_PER_HOUR` | 20 | Self-imposed rate limit |
| `IAMQ_ENABLED` | false | Enable inter-agent message queue |
| `IAMQ_HTTP_URL` | `http://127.0.0.1:18790` | IAMQ service URL |
| `IAMQ_AGENT_ID` | `instagram_agent` | This agent's ID in the queue |
| `EMBEDDINGS_URL` | `http://host.docker.internal:18795` | Embeddings service URL |

## Setup

```bash
cp .env.example .env
# Edit .env with your Instagram credentials and target accounts
docker compose run --rm agent status
docker compose run --rm agent engage --list a
```

## Development

```bash
poetry install --with dev
poetry run pipeline ci                              # full CI
poetry run pytest tests/ -v                         # tests only
poetry run ruff check src/ tests/ tools/            # lint
docker compose --profile cron up -d engage-cron     # scheduled loop
```

See `spec/ARCHITECTURE.md` for system design and `spec/LEARNINGS.md` for runtime learnings.

## Related

- [openclaw-inter-agent-message-queue](https://github.com/r3dlex/openclaw-inter-agent-message-queue) — IAMQ: message bus, agent registry, and cron scheduler
- [openclaw-main-agent](https://github.com/r3dlex/openclaw-main-agent) — Cross-agent pipeline orchestrator

## License

[MIT](LICENSE)
