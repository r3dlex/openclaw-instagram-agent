# Troubleshooting

## Common Issues

### "Challenge Required" error

Instagram detected automated behavior and requires verification.

**Fix:**
1. Log into Instagram manually from the same device/IP
2. Complete any verification challenge (SMS, email, captcha)
3. The agent will automatically retry API after the cooldown period (`API_RETRY_HOURS`, default 24h)
4. Meanwhile, browser fallback handles engagement

### Rate limit hit

The agent self-limits to `MAX_ACTIONS_PER_HOUR` (default 20). If Instagram's own rate limit is hit:

**Fix:**
1. The agent marks API as unavailable and switches to browser
2. Reduce `MAX_ACTIONS_PER_HOUR` in `.env`
3. Increase `MIN_ACTION_DELAY_SECONDS` and `MAX_ACTION_DELAY_SECONDS`

### Two-Factor Authentication (2FA) failures

Instagram requires a 2FA code but login fails.

**Fix:**
1. Ensure `IG_2FA_SEED` is set in `.env` with the base32 TOTP seed from your authenticator app setup
2. Verify the seed is correct by generating a code with `python -c "import pyotp; print(pyotp.TOTP('YOUR_SEED').now())"` and comparing with your authenticator app
3. If using SMS-based 2FA (not TOTP), switch to an authenticator app — SMS codes cannot be auto-generated
4. Session reuse (`session_cache/`) reduces how often 2FA is needed; delete `session_cache/session.json` to force a fresh login with 2FA

### Session expired / Login required

Session cookies become stale periodically.

**Fix:**
1. The agent auto-detects this and re-authenticates
2. If persistent, delete `session_cache/session.json` to force fresh login
3. Check that `INSTAGRAM_USERNAME` and `INSTAGRAM_PASSWORD` in `.env` are correct

### Browser fallback not working

CDP connection failures when trying to connect to running browser.

**Fix:**
1. Ensure the browser is running with remote debugging enabled
2. Check `BROWSER_CDP_HOST` and `BROWSER_CDP_PORT` in `.env`
3. If no running browser, the agent launches headless Chromium as fallback
4. Ensure Playwright browsers are installed: `playwright install chromium`

### Docker build fails

Missing system dependencies for Playwright.

**Fix:**
1. The Dockerfile includes all required system packages
2. If building on ARM (Apple Silicon), ensure Docker Desktop is up to date
3. Run `docker compose build --no-cache` to rebuild from scratch

## Logs

Check `./logs/` directory for structured JSON logs. Set `LOG_LEVEL=DEBUG` in `.env` for verbose output.

## Resetting State

```bash
# Reset API cooldown (force retry)
rm -f session_cache/api_failure_timestamp

# Reset session (force re-login)
rm -f session_cache/session.json

# Full reset
rm -rf session_cache/
```
