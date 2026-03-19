# TOOLS.md - Local Notes

This file is for environment-specific details. Keep it updated as you learn about your setup.

## Instagram CLI

```bash
./scripts/run.sh engage --list a   # Run engagement cycle
./scripts/run.sh dms --list a      # Check DMs
./scripts/run.sh status            # Show current status
```

## Browser Automation

The agent can connect to an existing browser via CDP for Instagram web automation. Configure `BROWSER_CDP_HOST` and `BROWSER_CDP_PORT` in `.env`.

## Logs

Check `./logs/` for structured JSON logs. Set `LOG_LEVEL=DEBUG` in `.env` for verbose output.

## Two-Factor Authentication

If your Instagram account has 2FA enabled, set `IG_2FA_SEED` in `.env` with your TOTP seed. The agent generates codes automatically during login. See `CONFIG.md` for details.

## Session State

- `session_cache/session.json` — Instagram API session (auto-managed, minimizes 2FA prompts)
- `session_cache/api_failure_timestamp` — API cooldown marker

To reset: `rm -rf session_cache/`

---

Add environment-specific notes below as you learn about your setup.
