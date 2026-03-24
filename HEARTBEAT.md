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
3. Reply via MQ for agent-to-agent responses:
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

**Important:** Reply through the MQ for agent-to-agent communication.

## 3. Engagement Cycle (if due)

Run the engagement cycle on List A accounts if sufficient time has passed since the last run:

```bash
openclaw-instagram engage --list a
```

Results are automatically broadcast to all peer agents via IAMQ.

## 4. Check DMs (if due)

```bash
openclaw-instagram dms --list a
```

New DMs are reported via IAMQ broadcast.

## Report to User

Send a Telegram summary ONLY when there's something worth reporting:
- Engagement runs completed, new DMs found, MQ requests processed.
  Example: "Liked 8 posts across 4 accounts. 1 new DM from @account."
- Rate limits, API failures, account issues: report IMMEDIATELY.
- Do NOT send a message if nothing happened. Silent heartbeats are fine.
