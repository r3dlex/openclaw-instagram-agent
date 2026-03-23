# Safety & Red Lines

> Non-negotiable rules for the Instagram Agent. These protect the account from bans, respect platform limits, and keep secrets safe.

## Human-Like Behavior

- **Delays between actions.** Wait 10-30 seconds between each Instagram action (like, view, scroll). Use Gaussian-jittered delays, not fixed intervals. See [ARCH-002](../.archgate/adrs/ARCH-002-human-like-rate-limiting.md).
- **Max 20 actions per hour.** Configurable via `$MAX_ACTIONS_PER_HOUR`. The rolling-hour rate limiter enforces this. Never bypass it.
- **No burst patterns.** Spread actions across the engagement window. Never like 20 posts in 2 minutes then go idle.

## API Cooldown

- **24-hour fallback on rate limit.** When Instagram returns a rate-limit or challenge response, immediately switch to Playwright browser mode for 24 hours. Do not retry the API.
- **Log the cooldown start time.** Resume API access only after the full cooldown period.
- **Broadcast cooldown notices** via IAMQ so the swarm is aware. See [COMMUNICATION.md](COMMUNICATION.md).

## Content Boundaries

- **No auto-replies to DMs.** DM monitoring is read-only. Surface new DMs to the user for manual response. Never send automated replies.
- **No content creation.** The agent likes posts and reels only. It must never post, comment, story, or send messages on behalf of the user. See [ARCH-006](../.archgate/adrs/ARCH-006-human-approval-for-text.md).
- **No following/unfollowing.** The agent does not manage the follow list.

## Credential Security

- **Session cookies are PII.** Instagram session files in `session_cache/` contain authentication state equivalent to a password. They are gitignored and must never be logged, shared, or included in IAMQ messages.
- **2FA seed is a secret.** Read from `$INSTAGRAM_2FA_SEED` at runtime only. Never log, never commit, never include in error reports.
- **All credentials from env.** `$INSTAGRAM_USERNAME`, `$INSTAGRAM_PASSWORD`, and `$INSTAGRAM_2FA_SEED` are resolved from `.env`. No hardcoding.

## Failure Modes

| Condition | Action |
|-----------|--------|
| API rate limit / challenge | Switch to browser fallback, broadcast cooldown |
| Login failure | Stop engagement, broadcast HIGH error, wait for human |
| Browser fallback fails | Stop engagement, log error, retry next cycle |
| Single action fails | Log, skip, continue with next target |
| IAMQ unreachable | Continue engagement, skip broadcasting |

The agent must never crash entirely due to a single failed action. Isolate failures and continue.

## Logging

- Log all actions with timestamp, target, action type, and result
- **No secrets in logs.** Redact session IDs, tokens, and 2FA values
- JSON structured logging to `logs/` (gitignored)

## Related

- Rate limiting ADR: [ARCH-002](../.archgate/adrs/ARCH-002-human-like-rate-limiting.md)
- Human approval ADR: [ARCH-006](../.archgate/adrs/ARCH-006-human-approval-for-text.md)
- Communication: [COMMUNICATION.md](COMMUNICATION.md)
- Troubleshooting: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---
*Owner: instagram_agent*
