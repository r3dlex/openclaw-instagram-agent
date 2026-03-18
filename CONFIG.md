# CONFIG.md - Runtime Configuration

## Environment

All configuration is via environment variables in `.env`. See `.env.example` for all available options.

Key variables:

| Variable | Purpose |
|----------|---------|
| `INSTAGRAM_USERNAME` | Instagram login |
| `INSTAGRAM_PASSWORD` | Instagram password |
| `TARGET_ACCOUNTS_A` | Comma-separated List A usernames |
| `TARGET_ACCOUNTS_B` | Comma-separated List B usernames |
| `TARGET_ACCOUNTS_C` | Comma-separated List C usernames |
| `BROWSER_CDP_HOST` | Browser CDP host for fallback |
| `BROWSER_CDP_PORT` | Browser CDP port for fallback |
| `MAX_ACTIONS_PER_HOUR` | Rate limit (default: 20) |
| `API_RETRY_HOURS` | Hours to wait before retrying API (default: 24) |

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

## Browser Fallback

When the API is rate-limited or challenged, the agent automatically falls back to browser automation via Playwright. It connects to an existing browser via CDP, or launches headless Chromium.

Configure CDP connection in `.env`:
- `BROWSER_CDP_HOST` — default `127.0.0.1`
- `BROWSER_CDP_PORT` — default `9222`

## Contact Lists

See `SOUL.md` for list definitions and engagement rules.

## Deep Docs

- `spec/ARCHITECTURE.md` — System design, ADR index, data flow
- `spec/PIPELINES.md` — CI pipelines and ADR enforcement
- `spec/TESTING.md` — Running and writing tests
- `spec/TROUBLESHOOTING.md` — Common issues and fixes
