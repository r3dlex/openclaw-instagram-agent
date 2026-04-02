# Learnings

This file is maintained by the OpenClaw agent. It records operational learnings, issues encountered, and solutions discovered during runtime.

> **For the agent:** When you encounter an issue, document it here with the date, what happened, and what you learned. This helps future sessions avoid the same pitfalls.

## Format

```
### YYYY-MM-DD - Brief title

**Issue:** What happened
**Root cause:** Why it happened
**Solution:** How it was fixed
**Lesson:** What to do differently next time
```

## Entries

### 2026-03-28 - Instagram 2FA not configured

**Issue:** Engagement run failed with "Instagram requires 2FA but IG_2FA_SEED is not set"
**Root cause:** .env has IG_2FA_SEED commented out. Instagram login requires 2FA.
**Solution:** André needs to provide a valid TOTP seed in .env as IG_2FA_SEED
**Lesson:** Without IG_2FA_SEED the API cannot login at all. Browser fallback is configured (CDP port 18800) but no browser is currently running on that port.

### 2026-03-28 - run.sh used wrong Docker command

**Issue:** run.sh used `docker compose run --rm` but `docker compose` (plugin) is not installed. Only `docker-compose` (standalone) exists on this system.
**Root cause:** Docker Desktop on this Mac has `docker-compose` standalone binary at /usr/local/bin/docker-compose, not the `docker compose` plugin.
**Solution:** Changed run.sh to check for `docker-compose` command instead of `docker compose`
**Lesson:** Test run.sh on cold start to catch Docker CLI mismatches before cron jobs fire.
