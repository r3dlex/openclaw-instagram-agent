"""Tests for the Telegram notifier."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from openclaw_instagram.utils.telegram import TelegramNotifier


def test_disabled_when_no_credentials():
    notifier = TelegramNotifier()
    assert not notifier.enabled
    assert notifier.send("hello") is False


def test_disabled_when_partial_credentials():
    notifier = TelegramNotifier(bot_token="tok")
    assert not notifier.enabled


def test_enabled_with_credentials():
    notifier = TelegramNotifier(bot_token="tok", chat_id="123")
    assert notifier.enabled


@patch("openclaw_instagram.utils.telegram.httpx.post")
def test_send_success(mock_post: MagicMock):
    mock_post.return_value = MagicMock(status_code=200)
    notifier = TelegramNotifier(bot_token="tok", chat_id="123")
    assert notifier.send("hello") is True
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert call_kwargs.kwargs["json"]["chat_id"] == "123"
    assert call_kwargs.kwargs["json"]["text"] == "hello"


@patch("openclaw_instagram.utils.telegram.httpx.post")
def test_send_failure(mock_post: MagicMock):
    mock_post.return_value = MagicMock(status_code=400, text="Bad Request")
    notifier = TelegramNotifier(bot_token="tok", chat_id="123")
    assert notifier.send("hello") is False


@patch("openclaw_instagram.utils.telegram.httpx.post")
def test_send_exception(mock_post: MagicMock):
    mock_post.side_effect = Exception("network error")
    notifier = TelegramNotifier(bot_token="tok", chat_id="123")
    assert notifier.send("hello") is False


@patch("openclaw_instagram.utils.telegram.httpx.post")
def test_notify_engagement_done(mock_post: MagicMock):
    mock_post.return_value = MagicMock(status_code=200)
    notifier = TelegramNotifier(bot_token="tok", chat_id="123")
    results = {
        "user1": {"liked": 3, "errors": []},
        "user2": {"liked": 2, "errors": ["timeout"]},
    }
    assert notifier.notify_engagement_done(results) is True
    msg = mock_post.call_args.kwargs["json"]["text"]
    assert "Liked: 5" in msg
    assert "timeout" in msg


@patch("openclaw_instagram.utils.telegram.httpx.post")
def test_notify_api_cooldown(mock_post: MagicMock):
    mock_post.return_value = MagicMock(status_code=200)
    notifier = TelegramNotifier(bot_token="tok", chat_id="123")
    assert notifier.notify_api_cooldown(24) is True
    msg = mock_post.call_args.kwargs["json"]["text"]
    assert "24h" in msg


def test_notify_dms_empty():
    notifier = TelegramNotifier(bot_token="tok", chat_id="123")
    assert notifier.notify_dms([]) is False


@patch("openclaw_instagram.utils.telegram.httpx.post")
def test_notify_dms(mock_post: MagicMock):
    mock_post.return_value = MagicMock(status_code=200)
    notifier = TelegramNotifier(bot_token="tok", chat_id="123")
    dms = [{"username": "alice", "preview": "hey there"}]
    assert notifier.notify_dms(dms) is True


@patch("openclaw_instagram.utils.telegram.httpx.post")
def test_notify_error(mock_post: MagicMock):
    mock_post.return_value = MagicMock(status_code=200)
    notifier = TelegramNotifier(bot_token="tok", chat_id="123")
    assert notifier.notify_error("login", "401 unauthorized") is True
    msg = mock_post.call_args.kwargs["json"]["text"]
    assert "login" in msg
    assert "401" in msg
