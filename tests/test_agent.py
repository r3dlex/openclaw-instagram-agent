"""Tests for agent orchestration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from openclaw_instagram.agent import InstagramAgent
from openclaw_instagram.config import Settings


def _make_settings(**overrides) -> Settings:
    defaults = dict(
        instagram_username="test",
        instagram_password="test",
        target_accounts_a="user1,user2",
        max_actions_per_hour=100,
        min_action_delay_seconds=0,
        max_action_delay_seconds=0,
    )
    defaults.update(overrides)
    return Settings(**defaults)


@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_engage_uses_api_when_available(mock_browser_cls, mock_api_cls, mock_log):
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api.api_available = True
    mock_api.get_user_id.return_value = 12345
    mock_media = MagicMock()
    mock_media.id = "media_1"
    mock_api.get_user_medias.return_value = [mock_media]
    mock_api.like_media.return_value = True
    mock_api_cls.return_value = mock_api

    agent = InstagramAgent(settings)
    results = agent.engage_accounts(["user1"])

    assert "user1" in results
    assert results["user1"]["method"] == "api"
    assert results["user1"]["liked"] == 1
    mock_api.get_user_id.assert_called_once_with("user1")


@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_engage_falls_back_to_browser(mock_browser_cls, mock_api_cls, mock_log):
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api.api_available = False
    mock_api_cls.return_value = mock_api

    mock_browser = MagicMock()
    mock_browser.like_latest_posts = MagicMock(return_value=2)

    async def fake_like(username, count=3):
        return 2

    mock_browser.like_latest_posts = fake_like
    mock_browser_cls.return_value = mock_browser

    agent = InstagramAgent(settings)
    results = agent.engage_accounts(["user1"])

    assert results["user1"]["method"] == "browser"
    assert results["user1"]["liked"] == 2
