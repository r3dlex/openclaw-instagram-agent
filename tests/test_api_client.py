"""Tests for Instagram API client, including 2FA/TOTP login."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from instagrapi.exceptions import TwoFactorRequired

from openclaw_instagram.api.client import InstagramAPIClient
from openclaw_instagram.config import Settings


def _make_settings(**overrides) -> Settings:
    defaults = dict(
        instagram_username="test_user",
        instagram_password="test_pass",
        target_accounts_a="",
        target_accounts_c="",
        max_actions_per_hour=100,
        min_action_delay_seconds=0,
        max_action_delay_seconds=0,
    )
    defaults.update(overrides)
    return Settings(**defaults)


@patch("openclaw_instagram.api.client.InstaClient")
def test_login_without_2fa(mock_cls, tmp_path):
    """Normal login works when 2FA is not required."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.get_settings.return_value = {"key": "val"}

    settings = _make_settings()
    api = InstagramAPIClient(settings)

    # Trigger login
    client = api._get_client()
    assert client is mock_client
    mock_client.login.assert_called_once_with("test_user", "test_pass")


@patch("openclaw_instagram.api.client.InstaClient")
def test_login_with_2fa_totp(mock_cls, tmp_path):
    """When 2FA is required and IG_2FA_SEED is set, TOTP code is generated."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.get_settings.return_value = {"key": "val"}

    # First login call raises TwoFactorRequired, second succeeds
    mock_client.login.side_effect = [TwoFactorRequired(), None]

    settings = _make_settings(ig_2fa_seed="JBSWY3DPEHPK3PXP")  # test base32 seed
    api = InstagramAPIClient(settings)

    client = api._get_client()
    assert client is mock_client
    assert mock_client.login.call_count == 2

    # Second call should include verification_code
    second_call = mock_client.login.call_args_list[1]
    assert "verification_code" in second_call.kwargs
    assert len(second_call.kwargs["verification_code"]) == 6


@patch("openclaw_instagram.api.client.InstaClient")
def test_login_2fa_no_seed_raises(mock_cls):
    """When 2FA is required but no seed is configured, raises RuntimeError."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.login.side_effect = TwoFactorRequired()

    settings = _make_settings(ig_2fa_seed="")
    api = InstagramAPIClient(settings)

    with pytest.raises(RuntimeError, match="IG_2FA_SEED is not set"):
        api._get_client()


@patch("openclaw_instagram.api.client.InstaClient")
def test_generate_2fa_code_returns_6_digits(mock_cls):
    """TOTP code generation returns a 6-digit string."""
    settings = _make_settings(ig_2fa_seed="JBSWY3DPEHPK3PXP")
    api = InstagramAPIClient(settings)

    code = api._generate_2fa_code()
    assert len(code) == 6
    assert code.isdigit()
