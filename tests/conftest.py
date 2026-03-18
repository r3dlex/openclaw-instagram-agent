"""Shared test fixtures."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from openclaw_instagram.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        instagram_username="test_user",
        instagram_password="test_pass",
        target_accounts_a="user1,user2,user3",
        target_accounts_b="user4,user5",
        target_accounts_c="user6",
        max_actions_per_hour=10,
        min_action_delay_seconds=0,
        max_action_delay_seconds=0,
    )


@pytest.fixture
def mock_instagrapi():
    with patch("openclaw_instagram.api.client.InstaClient") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.get_settings.return_value = {"key": "value"}
        yield mock_client


@pytest.fixture
def no_sleep():
    """Disable all sleeps for fast tests."""
    with (
        patch("openclaw_instagram.utils.human_delay.time.sleep"),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        yield
