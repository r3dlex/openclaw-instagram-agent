"""Configuration management loaded from environment variables."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
