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

### 2026-04-14 - Instagram API IP blacklist causes BadPassword exception, no browser fallback triggered

**Issue:** Hourly engagement cron fails with `instagrapi.exceptions.BadPassword: You can log in with your linked Facebook account. If you are sure that the password is correct, then change your IP address, because it is added to a blacklist of the Instagram Server`. This is Instagram's way of saying the IP is blacklisted due to rate limits, NOT an actual wrong password.

**Root cause:** Two problems:
1. `BadPassword` is not caught in `_safe_call()` (client.py) - only `RateLimitError`, `PleaseWaitFewMinutes`, `ChallengeRequired`, and `LoginRequired` are caught. The unhandled exception propagates up and crashes `engage_accounts()`.
2. Even if `_mark_api_failed()` were called, the `api_available` property has a logic bug: it only checks the failure timestamp when `self._api_available is False`. But `_api_available` starts as `True` in `__init__` and is only set to `False` by `_mark_api_failed()`. So the cooldown path never activates.

**Solution (code fix needed):**
1. Add `BadPassword` to the exception handling in `_safe_call()` to call `_mark_api_failed()` 
2. Fix the `api_available` property to always check the failure file regardless of `_api_available` state
3. OR: Add a try/except around the whole `_engage_via_api` call in `engage_accounts()` that catches `BadPassword`, calls `_mark_api_failed()`, and falls back to `_engage_via_browser()`

**Workaround (immediate):** The browser is available on port 18800 (Chrome running). A code fix is needed to properly fall back to browser when API returns this error.

**Lesson:** Instagram's API伪装成 "BadPassword" when the real issue is IP blacklist. The exception type is misleading. The code needs to handle this case explicitly AND the browser fallback path needs to be triggered properly.

## 2026-04-17 - IP Blacklisted by Instagram

**Issue:** Instagram API consistently returning `BadPassword` error with message:
"You can log in with your linked Facebook account. If you are sure that the password is correct, then change your IP address, because it is added to the blacklist of the Instagram Server"

**Impact:**
- API login fails for all accounts (ankes_insta, stuttgart_blog, stuttgartmitkind)
- Browser fallback also failing (connection refused on CDP)
- Both engagement and DM checks affected

**Attempted fallback:**
- Switched to browser mode via Playwright
- Browser launched headless but process timed out and was killed
- CDP connection refused on 127.0.0.1:18800

### 2026-04-21 - IP still blacklisted, browser fallback timing out

**Issue:** Same IP blacklist error persists. Browser launched headless but engagement timed out.
**Root cause:** IP remains on Instagram's blacklist. Browser fallback triggered but no CDP endpoint available.
**Solution:** None yet. Issue ongoing.
**Lesson:** Consider configuring VPN or proxy to change exit IP.

**Status:** Unable to perform engagement until IP is delisted or VPN/proxy is configured.

