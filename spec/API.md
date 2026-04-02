# API — openclaw-instagram-agent

## Overview

The Instagram agent does not expose an HTTP server. All cross-agent communication
uses IAMQ. Operators can also use the CLI directly (e.g. for manual engagement
runs or to check logs).

---

## IAMQ Message Interface

### Incoming messages accepted by `instagram_agent`

| Subject | Purpose | Body fields |
|---------|---------|-------------|
| `instagram.engage` | Trigger an immediate engagement cycle (like, comment, follow) | `mode?: "like"\|"comment"\|"follow"\|"all"` |
| `instagram.status` | Return last engagement run stats and session health | — |
| `instagram.pause` | Pause scheduled engagement (sets a pause flag) | `until?: "ISO8601"` |
| `instagram.resume` | Resume engagement after a pause | — |
| `instagram.report` | Return engagement statistics for a period | `days?: number` |
| `status` | Return agent process health and browser status | — |

#### Example: trigger an engagement cycle

```json
{
  "from": "agent_claude",
  "to": "instagram_agent",
  "type": "request",
  "priority": "NORMAL",
  "subject": "instagram.engage",
  "body": {"mode": "like"}
}
```

#### Example response

```json
{
  "from": "instagram_agent",
  "to": "agent_claude",
  "type": "response",
  "priority": "NORMAL",
  "subject": "instagram.engage.result",
  "body": {
    "mode": "like",
    "items_processed": 30,
    "rate_limited": false,
    "duration_seconds": 145,
    "timestamp": "2026-04-02T09:12:00Z"
  }
}
```

---

## CLI Interface

```bash
# Run a full engagement cycle (like + comment + follow)
poetry run instagram engage --mode all

# Like only
poetry run instagram engage --mode like

# Check status
poetry run instagram status

# View recent logs
poetry run instagram logs --tail 50
```

---

## Safety Constraints

The agent will refuse IAMQ requests that would exceed Instagram's unofficial
rate limits. See `spec/SAFETY.md` for per-action daily caps. Any `engage`
request arriving while the agent is already running an engagement cycle is
queued and processed after the current cycle completes.

---

## No Inbound Webhook

The agent does not listen for Instagram webhooks or notifications. It operates
purely in outbound mode — reading the feed and acting on it — using the
`instagrapi` API client with a Playwright browser fallback.

---

**Related:** `spec/COMMUNICATION.md`, `spec/SAFETY.md`, `spec/ARCHITECTURE.md`
