# Cron Schedules — openclaw-instagram-agent

## Overview

The Instagram agent runs two engagement sessions per day — a morning run and an
evening run — to distribute activity naturally and avoid triggering Instagram's
automation detection. All crons are registered with IAMQ on startup.

## Schedules

### morning_engage
- **Expression**: `0 9 * * *` (09:00 UTC daily)
- **Purpose**: Run a full engagement cycle: scroll home feed and explore,
  like eligible posts, leave contextual comments on selected posts, check
  follow-back queue and act. Uses `instagrapi` API client; falls back to
  Playwright browser if API session is stale.
- **Trigger**: Delivered via IAMQ message `cron::morning_engage`
- **Handler**: `openclaw_instagram.agent.run_engagement_cycle(mode="all")`
- **Expected duration**: 5–15 minutes (rate-limit delays built in)
- **On failure**: Log error to `logs/`; send IAMQ warning to `agent_claude`;
  do not retry until evening session to respect daily action caps

### evening_engage
- **Expression**: `0 19 * * *` (19:00 UTC daily)
- **Purpose**: Second engagement cycle. Focus on stories and explore-page content
  that has refreshed since morning. Lower comment volume in evening to avoid pattern.
- **Trigger**: Delivered via IAMQ message `cron::evening_engage`
- **Handler**: `openclaw_instagram.agent.run_engagement_cycle(mode="all", evening=True)`
- **Expected duration**: 5–12 minutes
- **On failure**: Log error; skip gracefully; do not retry

## Cron Registration

Registered with IAMQ on startup via `POST /crons`:

```json
[
  {"subject": "cron::morning_engage", "expression": "0 9 * * *"},
  {"subject": "cron::evening_engage", "expression": "0 19 * * *"}
]
```

## Pause / Resume

If the agent is paused via IAMQ `instagram.pause`, incoming `cron::` messages
are acknowledged but the engagement cycle is skipped. The pause state is stored
in `logs/pause_state.json` and survives process restarts.

## Daily Action Caps

Each cron run checks remaining daily budgets before acting. If a cap would be
exceeded, the run exits early. See `spec/SAFETY.md` for the specific limits.
The morning run consumes approximately 60% of the daily budget; the evening run
uses the remainder.

## Manual Trigger

```bash
# Force an engagement cycle immediately
poetry run instagram engage --mode all

# Or via IAMQ
curl -X POST http://127.0.0.1:18790/send \
  -H "Content-Type: application/json" \
  -d '{"from":"developer","to":"instagram_agent","type":"request","priority":"HIGH","subject":"instagram.engage","body":{"mode":"all"}}'
```

---

**Related:** `spec/API.md`, `spec/SAFETY.md`, `spec/COMMUNICATION.md`

## References

- [IAMQ Cron Subsystem](https://github.com/r3dlex/openclaw-inter-agent-message-queue/blob/main/spec/CRON.md) — how cron schedules are stored and fired
- [IAMQ API — Cron endpoints](https://github.com/r3dlex/openclaw-inter-agent-message-queue/blob/main/spec/API.md#cron-scheduling)
- [IamqSidecar.MqClient.register_cron/3](https://github.com/r3dlex/openclaw-inter-agent-message-queue/tree/main/sidecar) — Elixir sidecar helper
- [openclaw-main-agent](https://github.com/r3dlex/openclaw-main-agent) — orchestrates cron-triggered pipelines
