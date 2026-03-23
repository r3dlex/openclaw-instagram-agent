"""Tests for configuration loading."""

from openclaw_instagram.config import Settings


def test_default_settings():
    """Code defaults are applied when no env overrides are provided."""
    s = Settings(
        instagram_username="u",
        instagram_password="p",
        _env_file=None,  # Prevent .env from overriding code defaults
    )
    assert s.max_actions_per_hour == 20
    assert s.min_action_delay_seconds == 10
    assert s.api_retry_hours == 24


def test_accounts_parsing():
    s = Settings(
        instagram_username="u",
        instagram_password="p",
        target_accounts_a="a, b, c",
        target_accounts_b="",
    )
    assert s.accounts_a == ["a", "b", "c"]
    assert s.accounts_b == []


def test_accounts_empty_string():
    s = Settings(
        instagram_username="u",
        instagram_password="p",
        target_accounts_a="",
        target_accounts_c="",
    )
    assert s.accounts_a == []
    assert s.accounts_c == []
