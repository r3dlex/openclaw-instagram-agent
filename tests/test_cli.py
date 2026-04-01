"""Tests for the CLI entry point."""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from openclaw_instagram.cli import main
from openclaw_instagram.config import Settings


def _make_settings(**overrides) -> Settings:
    defaults = dict(
        instagram_username="test",
        instagram_password="test",
        target_accounts_a="user1,user2",
        target_accounts_b="user3",
        target_accounts_c="user4",
        max_actions_per_hour=100,
        min_action_delay_seconds=0,
        max_action_delay_seconds=0,
    )
    defaults.update(overrides)
    return Settings(**defaults)


def _make_agent_mock(settings: Settings | None = None):
    """Create a mock InstagramAgent."""
    agent = MagicMock()
    agent.api = MagicMock()
    agent.api.api_available = True
    agent.api.rate_limiter = MagicMock()
    agent.api.rate_limiter.count_this_hour = 5
    agent.iamq = MagicMock()
    agent.iamq.enabled = False
    agent.iamq.agent_id = "test_agent"
    return agent


@patch("openclaw_instagram.cli.get_settings")
@patch("openclaw_instagram.cli.InstagramAgent")
def test_engage_command_list_a(mock_agent_cls, mock_get_settings, capsys):
    """engage --list a runs engagement on accounts_a."""
    settings = _make_settings()
    mock_get_settings.return_value = settings

    agent = _make_agent_mock(settings)
    agent.engage_accounts.return_value = {
        "user1": {
            "method": "api", "liked": 2, "commented": 0,
            "skipped": 0, "posts": [], "errors": [],
        },
        "user2": {
            "method": "api", "liked": 1, "commented": 0,
            "skipped": 0, "posts": [], "errors": [],
        },
    }
    mock_agent_cls.return_value = agent

    with patch.object(sys, "argv", ["cli", "engage", "--list", "a"]):
        main()

    agent.engage_accounts.assert_called_once_with(["user1", "user2"])
    agent.close.assert_called_once()
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert "user1" in result


@patch("openclaw_instagram.cli.get_settings")
@patch("openclaw_instagram.cli.InstagramAgent")
def test_engage_command_list_b(mock_agent_cls, mock_get_settings, capsys):
    """engage --list b runs engagement on accounts_b."""
    settings = _make_settings()
    mock_get_settings.return_value = settings

    agent = _make_agent_mock(settings)
    agent.engage_accounts.return_value = {"user3": {"liked": 1}}
    mock_agent_cls.return_value = agent

    with patch.object(sys, "argv", ["cli", "engage", "--list", "b"]):
        main()

    agent.engage_accounts.assert_called_once_with(["user3"])


@patch("openclaw_instagram.cli.get_settings")
@patch("openclaw_instagram.cli.InstagramAgent")
def test_engage_command_empty_accounts_exits(mock_agent_cls, mock_get_settings):
    """engage with empty account list exits with code 1."""
    settings = _make_settings(target_accounts_a="")
    mock_get_settings.return_value = settings
    agent = _make_agent_mock(settings)
    mock_agent_cls.return_value = agent

    with (
        patch.object(sys, "argv", ["cli", "engage", "--list", "a"]),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()
    assert exc_info.value.code == 1


@patch("openclaw_instagram.cli.get_settings")
@patch("openclaw_instagram.cli.InstagramAgent")
def test_dms_command(mock_agent_cls, mock_get_settings, capsys):
    """dms command prints DMs from target accounts."""
    settings = _make_settings()
    mock_get_settings.return_value = settings

    agent = _make_agent_mock(settings)
    agent.check_dms.return_value = [
        {"username": "user1", "source": "api", "thread_id": "t1"}
    ]
    mock_agent_cls.return_value = agent

    with patch.object(sys, "argv", ["cli", "dms", "--list", "a"]):
        main()

    agent.check_dms.assert_called_once_with(filter_usernames=["user1", "user2"])
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result[0]["username"] == "user1"


@patch("openclaw_instagram.cli.get_settings")
@patch("openclaw_instagram.cli.InstagramAgent")
def test_status_command(mock_agent_cls, mock_get_settings, capsys):
    """status command prints agent status info."""
    settings = _make_settings()
    mock_get_settings.return_value = settings

    agent = _make_agent_mock(settings)
    mock_agent_cls.return_value = agent

    with patch.object(sys, "argv", ["cli", "status"]):
        main()

    captured = capsys.readouterr()
    assert "API available" in captured.out
    assert "Actions this hour" in captured.out
    assert "IAMQ" in captured.out


@patch("openclaw_instagram.cli.get_settings")
@patch("openclaw_instagram.cli.InstagramAgent")
def test_status_command_iamq_enabled(mock_agent_cls, mock_get_settings, capsys):
    """status command shows IAMQ peer info when enabled."""
    settings = _make_settings()
    mock_get_settings.return_value = settings

    agent = _make_agent_mock(settings)
    agent.iamq.enabled = True
    agent.get_peer_agents.return_value = [{"id": "other_agent"}]
    mock_agent_cls.return_value = agent

    with patch.object(sys, "argv", ["cli", "status"]):
        main()

    captured = capsys.readouterr()
    assert "other_agent" in captured.out


@patch("openclaw_instagram.cli.get_settings")
@patch("openclaw_instagram.cli.InstagramAgent")
def test_agents_command_when_iamq_disabled_exits(mock_agent_cls, mock_get_settings):
    """agents command exits with 1 when IAMQ disabled."""
    settings = _make_settings()
    mock_get_settings.return_value = settings

    agent = _make_agent_mock(settings)
    agent.iamq.enabled = False
    mock_agent_cls.return_value = agent

    with (
        patch.object(sys, "argv", ["cli", "agents"]),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()
    assert exc_info.value.code == 1


@patch("openclaw_instagram.cli.get_settings")
@patch("openclaw_instagram.cli.InstagramAgent")
def test_agents_command_when_iamq_enabled(mock_agent_cls, mock_get_settings, capsys):
    """agents command prints peer agents when IAMQ enabled."""
    settings = _make_settings()
    mock_get_settings.return_value = settings

    agent = _make_agent_mock(settings)
    agent.iamq.enabled = True
    agent.get_peer_agents.return_value = [{"id": "mail_agent"}]
    mock_agent_cls.return_value = agent

    with patch.object(sys, "argv", ["cli", "agents"]):
        main()

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result[0]["id"] == "mail_agent"


@patch("openclaw_instagram.cli.get_settings")
@patch("openclaw_instagram.cli.InstagramAgent")
def test_inbox_command_when_iamq_disabled_exits(mock_agent_cls, mock_get_settings):
    """inbox command exits with 1 when IAMQ disabled."""
    settings = _make_settings()
    mock_get_settings.return_value = settings

    agent = _make_agent_mock(settings)
    agent.iamq.enabled = False
    mock_agent_cls.return_value = agent

    with (
        patch.object(sys, "argv", ["cli", "inbox"]),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()
    assert exc_info.value.code == 1


@patch("openclaw_instagram.cli.get_settings")
@patch("openclaw_instagram.cli.InstagramAgent")
def test_inbox_command_when_iamq_enabled(mock_agent_cls, mock_get_settings, capsys):
    """inbox command prints messages when IAMQ enabled."""
    settings = _make_settings()
    mock_get_settings.return_value = settings

    agent = _make_agent_mock(settings)
    agent.iamq.enabled = True
    agent.poll_iamq.return_value = [{"id": "msg1", "subject": "Hello"}]
    mock_agent_cls.return_value = agent

    with patch.object(sys, "argv", ["cli", "inbox"]):
        main()

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result[0]["id"] == "msg1"


@patch("openclaw_instagram.cli.get_settings")
@patch("openclaw_instagram.cli.InstagramAgent")
def test_no_command_exits(mock_agent_cls, mock_get_settings):
    """Running with no subcommand prints help and exits with 1."""
    settings = _make_settings()
    mock_get_settings.return_value = settings
    mock_agent_cls.return_value = _make_agent_mock(settings)

    with (
        patch.object(sys, "argv", ["cli"]),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()
    assert exc_info.value.code == 1


@patch("openclaw_instagram.cli.get_settings")
@patch("openclaw_instagram.cli.InstagramAgent")
def test_close_called_on_exception(mock_agent_cls, mock_get_settings):
    """agent.close() is always called even if engage raises."""
    settings = _make_settings()
    mock_get_settings.return_value = settings

    agent = _make_agent_mock(settings)
    agent.engage_accounts.side_effect = RuntimeError("boom")
    mock_agent_cls.return_value = agent

    with (
        patch.object(sys, "argv", ["cli", "engage", "--list", "a"]),
        pytest.raises(RuntimeError),
    ):
        main()

    agent.close.assert_called_once()


@patch("openclaw_instagram.cli.get_settings")
@patch("openclaw_instagram.cli.InstagramAgent")
def test_engage_command_list_c(mock_agent_cls, mock_get_settings, capsys):
    """engage --list c runs engagement on accounts_c."""
    settings = _make_settings()
    mock_get_settings.return_value = settings

    agent = _make_agent_mock(settings)
    agent.engage_accounts.return_value = {"user4": {"liked": 1}}
    mock_agent_cls.return_value = agent

    with patch.object(sys, "argv", ["cli", "engage", "--list", "c"]):
        main()

    agent.engage_accounts.assert_called_once_with(["user4"])


@patch("openclaw_instagram.cli.get_settings")
@patch("openclaw_instagram.cli.InstagramAgent")
def test_dms_command_empty_accounts(mock_agent_cls, mock_get_settings, capsys):
    """dms with empty accounts calls check_dms with None."""
    settings = _make_settings(target_accounts_a="")
    mock_get_settings.return_value = settings

    agent = _make_agent_mock(settings)
    agent.check_dms.return_value = []
    mock_agent_cls.return_value = agent

    with patch.object(sys, "argv", ["cli", "dms", "--list", "a"]):
        main()

    # When accounts is empty, filter_usernames should be None
    agent.check_dms.assert_called_once_with(filter_usernames=None)
