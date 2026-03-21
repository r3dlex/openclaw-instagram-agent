# BOOT.md - Startup Tasks

On first session or cold start, execute these steps before normal operations.

## 1. Register with Inter-Agent Message Queue

Register yourself with the IAMQ so peer agents can discover and message you:

```bash
curl -s -X POST http://127.0.0.1:18790/register \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "instagram_agent",
    "name": "InstaOps 📸",
    "emoji": "📸",
    "description": "Autonomous Instagram engagement agent — likes posts/reels, monitors DMs, reports via Telegram",
    "capabilities": ["instagram_engage", "instagram_dms", "instagram_like", "instagram_status"],
    "workspace": "/Users/redlexgilgamesh/Ws/Openclaw/openclaw-instagram-agent"
  }'
```

Or via the Python CLI (which registers automatically on startup):

```bash
openclaw-instagram status
```

## 2. Check IAMQ Inbox

After registering, check for any pending messages from other agents:

```bash
curl -s "http://127.0.0.1:18790/inbox/instagram_agent?status=unread"
```

Process messages in chronological order. For each:
1. Read and understand the request
2. Mark as read: `PATCH /messages/:id {"status": "read"}`
3. Act on it if applicable
4. Reply via `POST /send` with `replyTo` set to the original message `id`
5. Mark as acted: `PATCH /messages/:id {"status": "acted"}`

## 3. Verify Instagram Session

```bash
openclaw-instagram status
```

If session is expired, re-login happens automatically (2FA via TOTP if configured).

## 4. Done

After boot tasks complete, proceed to normal operations per `AGENTS.md` and `HEARTBEAT.md`.
