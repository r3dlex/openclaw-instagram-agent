# HEARTBEAT.md - Periodic Tasks

On every heartbeat, execute these tasks in order.

## 1. IAMQ Heartbeat

Keep your registration alive so peer agents know you're online:

```bash
curl -X POST http://127.0.0.1:18790/heartbeat \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "instagram_agent"}'
```

## 2. Check IAMQ Inbox

Poll for unread messages from other agents:

```bash
curl -s "http://127.0.0.1:18790/inbox/instagram_agent?status=unread"
```

For each message:
1. Mark as read: `PATCH http://127.0.0.1:18790/messages/:id {"status": "read"}`
2. Process the request (if `type: "request"`)
3. Reply via MQ (not Telegram) for agent-to-agent responses:
   ```bash
   curl -X POST http://127.0.0.1:18790/send \
     -H "Content-Type: application/json" \
     -d '{
       "from": "instagram_agent",
       "to": "<requesting_agent_id>",
       "type": "response",
       "subject": "Re: <original subject>",
       "body": "<your response>",
       "replyTo": "<original-message-id>"
     }'
   ```
4. Mark as acted: `PATCH http://127.0.0.1:18790/messages/:id {"status": "acted"}`

**Important:** Reply through the MQ for agent-to-agent communication. Telegram is for human-facing output only.

## 3. Engagement Cycle (if due)

Run the engagement cycle on List A accounts if sufficient time has passed since the last run:

```bash
openclaw-instagram engage --list a
```

Results are automatically broadcast to all peer agents via IAMQ and to Telegram.

## 4. Check DMs (if due)

```bash
openclaw-instagram dms --list a
```

New DMs are reported via IAMQ broadcast and Telegram notification.
