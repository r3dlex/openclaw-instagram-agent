"""Configuration management loaded from environment variables.

Telegram credentials are resolved from ~/.openclaw/openclaw.json
(the central OpenClaw config) rather than per-agent .env files.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenClaw config resolver — reads Telegram credentials from the central
# ~/.openclaw/openclaw.json instead of per-agent env vars.
# ---------------------------------------------------------------------------

_OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"
_OPENCLAW_CREDENTIALS = Path.home() / ".openclaw" / "credentials"


def _resolve_telegram(agent_id: str) -> tuple[str, str]:
    """Resolve (bot_token, chat_id) for *agent_id* from ~/.openclaw/openclaw.json.

    Lookup chain:
      1. bindings[] → find entry where agentId == agent_id → accountId
      2. channels.telegram.accounts[accountId].botToken
      3. credentials/telegram-{accountId}-allowFrom.json → first allowFrom entry
    Returns ("", "") if anything is missing so callers degrade gracefully.
    """
    try:
        cfg = json.loads(_OPENCLAW_CONFIG.read_text())
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        _log.debug("openclaw config not found or invalid: %s", exc)
        return "", ""

    # 1. Resolve binding → telegram accountId
    account_id = ""
    for binding in cfg.get("bindings", []):
        match = binding.get("match", {})
        if (
            binding.get("agentId") == agent_id
            and match.get("channel") == "telegram"
        ):
            account_id = match.get("accountId", "")
            break
    if not account_id:
        _log.debug("no telegram binding for agent %s", agent_id)
        return "", ""

    # 2. Resolve botToken
    accounts = cfg.get("channels", {}).get("telegram", {}).get("accounts", {})
    bot_token = accounts.get(account_id, {}).get("botToken", "")
    if not bot_token:
        _log.debug("no botToken for account %s", account_id)
        return "", ""

    # 3. Resolve chatId from allowFrom credentials
    chat_id = ""
    allow_file = _OPENCLAW_CREDENTIALS / f"telegram-{account_id}-allowFrom.json"
    try:
        allow_data = json.loads(allow_file.read_text())
        allow_list = allow_data.get("allowFrom", [])
        if allow_list:
            chat_id = str(allow_list[0])
    except (FileNotFoundError, json.JSONDecodeError):
        _log.debug("no allowFrom file for %s", account_id)

    return bot_token, chat_id


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Instagram credentials
    instagram_username: str = ""
    instagram_password: str = ""
    ig_2fa_seed: str = ""  # TOTP seed for 2FA (from authenticator app setup)

    # Instagram Graph API (optional)
    instagram_access_token: str = ""
    instagram_app_secret: str = ""
    instagram_business_account_id: str = ""

    # Target accounts (comma-separated)
    target_accounts_a: str = ""
    target_accounts_b: str = ""
    target_accounts_c: str = ""

    # Browser automation
    browser_cdp_host: str = "127.0.0.1"
    browser_cdp_port: int = 9222

    # Rate limiting
    max_actions_per_hour: int = 20
    min_action_delay_seconds: int = 10
    max_action_delay_seconds: int = 30
    api_retry_hours: int = 24

    # Inter-Agent Message Queue (IAMQ)
    iamq_http_url: str = "http://127.0.0.1:18790"
    iamq_agent_id: str = "instagram_agent"
    iamq_enabled: bool = False
    iamq_heartbeat_interval: int = 240  # seconds between heartbeats
    iamq_poll_interval: int = 30  # seconds between inbox polls

    # Logging
    log_level: str = "INFO"
    log_dir: Path = Field(default=Path("./logs"))

    @property
    def telegram_bot_token(self) -> str:
        """Resolved from ~/.openclaw/openclaw.json (not env vars)."""
        token, _ = _resolve_telegram(self.iamq_agent_id)
        return token

    @property
    def telegram_chat_id(self) -> str:
        """Resolved from ~/.openclaw/openclaw.json credentials."""
        _, chat_id = _resolve_telegram(self.iamq_agent_id)
        return chat_id

    @property
    def accounts_a(self) -> list[str]:
        return [a.strip() for a in self.target_accounts_a.split(",") if a.strip()]

    @property
    def accounts_b(self) -> list[str]:
        return [a.strip() for a in self.target_accounts_b.split(",") if a.strip()]

    @property
    def accounts_c(self) -> list[str]:
        return [a.strip() for a in self.target_accounts_c.split(",") if a.strip()]


def get_settings() -> Settings:
    return Settings()
