# Architecture

## Overview

The OpenClaw Instagram Agent automates engagement with target Instagram accounts. It operates as an autonomous OpenClaw agent with human oversight for sensitive actions (replies, DMs).

Architecture decisions are documented as ADRs in `.archgate/adrs/` and enforced by pipelines (see [PIPELINES.md](PIPELINES.md)).

```
┌─────────────────────────────────────────┐
│           OpenClaw Gateway              │
│  (WhatsApp / Telegram / Discord / Web)  │
└────────────────┬────────────────────────┘
                 │ heartbeat / commands
                 ▼
┌─────────────────────────────────────────┐
│         Instagram Agent (Python)        │
│                                         │
│  ┌──────────┐    ┌──────────────────┐   │
│  │ API      │◄──►│ Rate Limiter     │   │
│  │ Client   │    │ (per-hour caps)  │   │
│  │(instagrapi)   └──────────────────┘   │
│  └────┬─────┘                           │
│       │ fallback after 24h cooldown     │
│       ▼                                 │
│  ┌──────────┐                           │
│  │ Browser  │                           │
│  │ Fallback │                           │
│  │(Playwright)                          │
│  └──────────┘                           │
└─────────────────────────────────────────┘
```

## Architecture Decision Records

All key decisions are tracked as ADRs in `.archgate/adrs/` following the [archgate](https://github.com/archgate/cli) format. Each ADR includes rationale, consequences, and which pipeline enforces it.

| ADR | Decision | Domain | Status |
|-----|----------|--------|--------|
| [ARCH-001](../.archgate/adrs/ARCH-001-api-first-browser-fallback.md) | API-first with browser fallback | instagram-client | accepted |
| [ARCH-002](../.archgate/adrs/ARCH-002-human-like-rate-limiting.md) | Human-like rate limiting | safety | accepted |
| [ARCH-003](../.archgate/adrs/ARCH-003-env-only-configuration.md) | Env-only configuration | configuration | accepted |
| [ARCH-004](../.archgate/adrs/ARCH-004-zero-install-execution.md) | Zero-install execution | deployment | accepted |
| [ARCH-005](../.archgate/adrs/ARCH-005-pipeline-assured-quality.md) | Pipeline-assured quality | quality | accepted |
| [ARCH-006](../.archgate/adrs/ARCH-006-human-approval-for-text.md) | Human approval for text output | safety | accepted |

## Components

### 1. API Client (`src/openclaw_instagram/api/client.py`)

> ADR: [ARCH-001](../.archgate/adrs/ARCH-001-api-first-browser-fallback.md)

Primary method using [instagrapi](https://github.com/subzeroid/instagrapi), a maintained Python wrapper for Instagram's private API.

- **Session persistence**: Saves/restores session cookies to `session_cache/`
- **2FA/TOTP support**: Automatic TOTP code generation via `pyotp` when `IG_2FA_SEED` is configured
- **Human-like delays**: Gaussian-jittered delays (see ARCH-002)
- **Self-imposed rate limits**: Configurable `MAX_ACTIONS_PER_HOUR`
- **Automatic cooldown**: On rate limit or challenge, marks API unavailable for `API_RETRY_HOURS`

### 2. Browser Fallback (`src/openclaw_instagram/browser/fallback.py`)

> ADR: [ARCH-001](../.archgate/adrs/ARCH-001-api-first-browser-fallback.md)

Activated when API enters cooldown. Uses Playwright to:
- Connect to existing browser via CDP (Chrome DevTools Protocol)
- Or launch headless Chromium with mobile viewport
- Perform likes, check DMs through the Instagram web interface

### 3. Rate Limiter (`src/openclaw_instagram/utils/human_delay.py`)

> ADR: [ARCH-002](../.archgate/adrs/ARCH-002-human-like-rate-limiting.md)

- Gaussian-jittered delays between all actions
- Rolling-hour action counter with configurable cap
- Blocks execution when hourly limit is reached

### 4. Agent Orchestrator (`src/openclaw_instagram/agent.py`)

Coordinates between API and browser:
1. Checks if API is available (not in cooldown)
2. Routes engagement through API or browser accordingly
3. Collects results and reports back
4. Never sends text without human approval (ARCH-006)

### 5. Configuration (`src/openclaw_instagram/config.py`)

> ADR: [ARCH-003](../.archgate/adrs/ARCH-003-env-only-configuration.md)

All config via environment variables (`.env` file), validated by Pydantic Settings.

### 6. Logging (`src/openclaw_instagram/utils/logging.py`)

Dual-output structured logging:
- **Console**: Human-readable via `structlog.dev.ConsoleRenderer`
- **File**: JSON lines to `logs/agent-YYYY-MM-DD.log` for machine parsing

### 7. IAMQ Client (`src/openclaw_instagram/utils/iamq.py`)

HTTP client for the [Inter-Agent Message Queue](https://github.com/r3dlex/openclaw-inter-agent-message-queue) service. Enables agent-to-agent communication:
- **Registration**: Announces presence on startup
- **Heartbeat**: Background thread keeps registration alive (every 4 min)
- **Messaging**: Sends direct messages or broadcasts to all peers
- **Inbox polling**: Fetches unread messages from other agents
- **Discovery**: Lists all registered peer agents
- Gracefully no-ops when disabled or when the IAMQ service is unreachable

### 8. Pipeline Runner (`tools/pipeline_runner/`)

> ADR: [ARCH-005](../.archgate/adrs/ARCH-005-pipeline-assured-quality.md)

Python-based CI pipelines that enforce ADRs and project quality. See [PIPELINES.md](PIPELINES.md).

## Data Flow

```
Heartbeat/Command → Agent.engage_accounts(list_a)
  → For each username:
    → If API available: API.get_user_medias() → API.like_media()
    → If API cooldown:  Browser.like_latest_posts()
    → Human delay between accounts (ARCH-002)
  → IAMQ: broadcast engagement results to peer agents
  → Return summary report
```

## Safety Mechanisms

| Mechanism | ADR | Purpose |
|-----------|-----|---------|
| Rate limiter | ARCH-002 | Max N actions per rolling hour |
| Human delays | ARCH-002 | Gaussian-jittered pauses between actions |
| API cooldown | ARCH-001 | 24h fallback to browser on rate limit |
| Session reuse | ARCH-001 | Reduces login frequency |
| Reply approval | ARCH-006 | All text replies require human approval |
| Secret scan | ARCH-003 | No credentials in tracked files |
| IAMQ broadcasts | — | Peer agents informed of status changes and errors |
| File logging | — | JSON audit trail in `logs/` |

## Deployment

> ADR: [ARCH-004](../.archgate/adrs/ARCH-004-zero-install-execution.md)

See [README.md](../README.md) for Docker and Poetry setup.

## Quality Assurance

> ADR: [ARCH-005](../.archgate/adrs/ARCH-005-pipeline-assured-quality.md)

See [PIPELINES.md](PIPELINES.md) for pipeline details and [TESTING.md](TESTING.md) for test guide.
