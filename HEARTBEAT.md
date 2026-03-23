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

## 5. Report to User

After completing all checks above, **send a summary to the user via your messaging channel** (Telegram through OpenClaw gateway). The user cannot see IAMQ messages.

- If you ran engagement, found DMs, or processed MQ requests: summarize what happened.
  Example: "Heartbeat: liked 8 posts across 4 accounts. 1 new DM from @account (flagged for review)."
- If nothing happened: "All quiet — no new DMs, engagement on schedule."
- Errors and warnings (rate limits, API failures): report IMMEDIATELY, don't wait for the heartbeat summary.
