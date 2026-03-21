# CONFIG.md - Runtime Configuration

## Environment

All configuration is via environment variables in `.env`. See `.env.example` for all available options.

Key variables:

| Variable | Purpose |
|----------|---------|
| `INSTAGRAM_USERNAME` | Instagram login |
| `INSTAGRAM_PASSWORD` | Instagram password |
| `IG_2FA_SEED` | TOTP seed for 2FA auto-login (optional) |
| `TARGET_ACCOUNTS_A` | Comma-separated List A usernames |
| `TARGET_ACCOUNTS_B` | Comma-separated List B usernames |
| `TARGET_ACCOUNTS_C` | Comma-separated List C usernames |
| `BROWSER_CDP_HOST` | Browser CDP host for fallback |
| `BROWSER_CDP_PORT` | Browser CDP port for fallback |
| `MAX_ACTIONS_PER_HOUR` | Rate limit (default: 20) |
| `API_RETRY_HOURS` | Hours to wait before retrying API (default: 24) |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token (optional) |
| `TELEGRAM_CHAT_ID` | Telegram chat ID for notifications (optional) |
| `LOG_LEVEL` | Logging level (default: INFO) |
| `LOG_DIR` | Directory for JSON log files (default: ./logs) |
| `IAMQ_ENABLED` | Enable inter-agent message queue (default: false) |
| `IAMQ_HTTP_URL` | IAMQ service URL (default: http://127.0.0.1:18790) |
| `IAMQ_AGENT_ID` | Agent identity in the queue (default: instagram_agent) |
| `IAMQ_HEARTBEAT_INTERVAL` | Heartbeat interval in seconds (default: 240) |
| `IAMQ_POLL_INTERVAL` | Inbox poll interval in seconds (default: 30) |

## Tools

Run engagement via CLI:

```bash
./scripts/run.sh engage --list a   # Engage List A
./scripts/run.sh dms --list a      # Check DMs from List A
./scripts/run.sh status            # Show status
```

Or via Docker:

```bash
docker compose run --rm agent engage --list a
```

## Two-Factor Authentication (2FA)

If your Instagram account has 2FA enabled with an authenticator app (TOTP), set `IG_2FA_SEED` in `.env` to the base32 seed from your authenticator setup QR code. The agent will auto-generate 2FA codes during login — no manual input needed.

If `IG_2FA_SEED` is not set and Instagram requires 2FA, login will fail with a clear error message.

Session reuse (`session_cache/`) means 2FA is only needed on fresh logins or session expiry.

## Browser Fallback

When the API is rate-limited or challenged, the agent automatically falls back to browser automation via Playwright. It connects to an existing browser via CDP, or launches headless Chromium.

Configure CDP connection in `.env`:
- `BROWSER_CDP_HOST` — default `127.0.0.1`
- `BROWSER_CDP_PORT` — default `9222`

## Telegram Notifications

When `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set, the agent sends notifications for:
- Engagement cycle completions (accounts processed, likes, errors)
- API cooldown activation (with retry time)
- New DMs requiring attention
- Critical errors

If credentials are not set, notifications silently no-op.

## Inter-Agent Message Queue (IAMQ)

When `IAMQ_ENABLED=true`, the agent registers with the [openclaw-inter-agent-message-queue](https://github.com/r3dlex/openclaw-inter-agent-message-queue) service for peer-to-peer communication with other agents.

On startup, the agent:
1. Registers with the queue using `IAMQ_AGENT_ID`
2. Starts a background heartbeat thread (every `IAMQ_HEARTBEAT_INTERVAL` seconds)
3. Broadcasts engagement summaries, errors, and API cooldowns to all peer agents

CLI commands for IAMQ:
```bash
openclaw-instagram agents   # List registered peer agents
openclaw-instagram inbox    # Check unread messages from other agents
openclaw-instagram status   # Shows IAMQ status and peer count
```

If the IAMQ service is not running, all messaging operations gracefully no-op.

## Logging

The agent writes JSON-formatted logs to `logs/agent-YYYY-MM-DD.log` daily. Console output uses human-readable format. Configure via `LOG_LEVEL` and `LOG_DIR` in `.env`.

## Contact Lists

See `SOUL.md` for list definitions and engagement rules.

## Deep Docs

- `spec/ARCHITECTURE.md` — System design, ADR index, data flow
- `spec/PIPELINES.md` — CI pipelines and ADR enforcement
- `spec/TESTING.md` — Running and writing tests
- `spec/TROUBLESHOOTING.md` — Common issues and fixes
