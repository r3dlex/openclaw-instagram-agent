# Communication

> How the Instagram Agent communicates with the swarm via IAMQ.

## IAMQ Registration

The agent registers on startup at `$IAMQ_HTTP_URL`.

```json
{
  "agent_id": "instagram_agent",
  "capabilities": [
    "instagram_engagement",
    "post_liking",
    "reel_liking",
    "dm_monitoring",
    "engagement_reporting",
    "browser_fallback"
  ]
}
```

## Outgoing Messages

### Engagement Cycle Results (broadcast)

After each engagement cycle, the agent broadcasts a summary to all agents.

```json
{
  "from": "instagram_agent",
  "to": "broadcast",
  "type": "info",
  "priority": "NORMAL",
  "subject": "Engagement cycle complete — 2026-03-23",
  "body": "Targets: 5 | Liked: 12 posts, 3 reels | Skipped: 2 (already liked)\nDuration: 8m 42s | Rate: 15/20 hourly limit"
}
```

### Error Alerts (broadcast, HIGH priority)

When a critical error occurs (login failure, account restriction, unexpected ban), broadcast immediately.

```json
{
  "from": "instagram_agent",
  "to": "broadcast",
  "type": "error",
  "priority": "HIGH",
  "subject": "Instagram API error — account restricted",
  "body": "Action: like_post | Error: login_required\nAPI returned challenge_required. Switching to 24h cooldown.\nManual 2FA re-auth may be needed."
}
```

### API Cooldown Notices (broadcast)

When the agent enters a rate-limit cooldown, notify the swarm.

```json
{
  "from": "instagram_agent",
  "to": "broadcast",
  "type": "info",
  "priority": "NORMAL",
  "subject": "Instagram API cooldown — 24h browser fallback",
  "body": "Rate limit hit at 2026-03-23T14:00:00Z.\nFalling back to Playwright browser mode.\nAPI access resumes: 2026-03-24T14:00:00Z"
}
```

## Incoming Messages

The agent does not currently handle incoming IAMQ requests. All engagement is driven by its own schedule and target list.

## Peer Agents

| Agent | Relationship |
|-------|-------------|
| `broadcast` | Receives engagement reports, error alerts, cooldown notices |

## Message Rules

- Keep broadcast bodies under 500 characters
- Never include Instagram credentials, session tokens, or 2FA seeds in messages
- Never include target account passwords or private data
- Error alerts use `priority: "HIGH"` — reserve for actionable failures only

## Related

- Architecture: [ARCHITECTURE.md](ARCHITECTURE.md)
- Safety rules: [SAFETY.md](SAFETY.md)
- Pipelines: [PIPELINES.md](PIPELINES.md)

---
*Owner: instagram_agent*

## References

- [IAMQ HTTP API](https://github.com/r3dlex/openclaw-inter-agent-message-queue/blob/main/spec/API.md)
- [IAMQ WebSocket Protocol](https://github.com/r3dlex/openclaw-inter-agent-message-queue/blob/main/spec/PROTOCOL.md)
- [IAMQ Cron Scheduling](https://github.com/r3dlex/openclaw-inter-agent-message-queue/blob/main/spec/CRON.md)
- [Sidecar Client](https://github.com/r3dlex/openclaw-inter-agent-message-queue/tree/main/sidecar)
- [openclaw-main-agent](https://github.com/r3dlex/openclaw-main-agent)
