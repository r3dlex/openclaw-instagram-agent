---
id: ARCH-006
title: Human Approval Required for Text Output
status: accepted
date: 2026-03-18
domain: safety
enforced_by: pipeline:ci
---

# ARCH-006: Human Approval Required for Text Output

## Status

Accepted

## Context

The agent interacts with real Instagram accounts. Automated replies or comments could damage relationships, violate platform rules, or misrepresent the user. Likes are low-risk; text is high-risk.

## Decision

- The agent may autonomously like posts, reels, and stories
- The agent must NEVER send DMs, comments, or any text without explicit human approval
- All proposed text is surfaced as a report with status "Awaiting user approval"
- The reporting format is defined in `SOUL.md`

## Consequences

- **Positive:** No accidental or inappropriate automated messages
- **Positive:** User maintains full control over their voice
- **Negative:** Reply latency depends on human availability
- **Negative:** Cannot fully automate conversation workflows

## Enforcement

- `SOUL.md` codifies the rule
- Agent orchestrator does not expose any `send_message` or `post_comment` method
- Code review gates any addition of text-sending capabilities
