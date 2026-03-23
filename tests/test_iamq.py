"""Tests for Inter-Agent Message Queue (IAMQ) client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from openclaw_instagram.utils.iamq import IAMQClient


def _make_client(**overrides) -> IAMQClient:
    defaults = dict(
        base_url="http://localhost:18790",
        agent_id="test_agent",
        enabled=True,
    )
    defaults.update(overrides)
    return IAMQClient(**defaults)


def test_disabled_noop():
    """When disabled, all methods return falsy without making HTTP calls."""
    client = IAMQClient(enabled=False)
    assert client.register() is False
    assert client.heartbeat() is False
    assert client.send("other", "sub", "body") is None
    assert client.inbox() == []
    assert client.update_status("id", "read") is False
    assert client.get_agents() == []
    assert client.get_status() is None


@patch("openclaw_instagram.utils.iamq.httpx.post")
def test_register_success(mock_post):
    """Successful registration returns True and sends full metadata."""
    mock_post.return_value = MagicMock(status_code=200)
    client = _make_client()
    assert client.register() is True
    mock_post.assert_called_once()
    payload = mock_post.call_args.kwargs["json"]
    assert payload["agent_id"] == "test_agent"
    # Registration must include discovery metadata
    assert "name" in payload
    assert "emoji" in payload
    assert "description" in payload
    assert "capabilities" in payload
    assert isinstance(payload["capabilities"], list)
    assert "workspace" in payload


@patch("openclaw_instagram.utils.iamq.httpx.post")
def test_register_failure(mock_post):
    """Failed registration returns False."""
    mock_post.return_value = MagicMock(status_code=500, text="error")
    client = _make_client()
    assert client.register() is False


@patch("openclaw_instagram.utils.iamq.httpx.post")
def test_register_network_error(mock_post):
    """Network error during registration returns False."""
    mock_post.side_effect = httpx.ConnectError("Connection refused")
    client = _make_client()
    assert client.register() is False


@patch("openclaw_instagram.utils.iamq.httpx.post")
def test_heartbeat_success(mock_post):
    """Successful heartbeat returns True."""
    mock_post.return_value = MagicMock(status_code=200)
    client = _make_client()
    assert client.heartbeat() is True


@patch("openclaw_instagram.utils.iamq.httpx.post")
def test_send_success(mock_post):
    """Successful send returns message dict."""
    mock_post.return_value = MagicMock(
        status_code=201,
        json=MagicMock(return_value={"id": "msg-123", "status": "unread"}),
    )
    client = _make_client()
    result = client.send("other_agent", "Hello", "Test body")
    assert result is not None
    assert result["id"] == "msg-123"
    payload = mock_post.call_args.kwargs["json"]
    assert payload["from"] == "test_agent"
    assert payload["to"] == "other_agent"
    assert payload["subject"] == "Hello"


@patch("openclaw_instagram.utils.iamq.httpx.post")
def test_send_with_reply_to(mock_post):
    """Send with replyTo includes it in payload."""
    mock_post.return_value = MagicMock(
        status_code=201,
        json=MagicMock(return_value={"id": "msg-456"}),
    )
    client = _make_client()
    client.send("other", "Re: Hello", "Reply", reply_to="msg-123")
    payload = mock_post.call_args.kwargs["json"]
    assert payload["replyTo"] == "msg-123"


@patch("openclaw_instagram.utils.iamq.httpx.get")
def test_inbox_success(mock_get):
    """Inbox returns list of messages."""
    mock_get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value={"messages": [{"id": "m1"}, {"id": "m2"}]}),
    )
    client = _make_client()
    msgs = client.inbox()
    assert len(msgs) == 2
    assert msgs[0]["id"] == "m1"


@patch("openclaw_instagram.utils.iamq.httpx.get")
def test_inbox_empty(mock_get):
    """Empty inbox returns empty list."""
    mock_get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value={"messages": []}),
    )
    client = _make_client()
    assert client.inbox() == []


@patch("openclaw_instagram.utils.iamq.httpx.patch")
def test_update_status_success(mock_patch):
    """Status update returns True on success."""
    mock_patch.return_value = MagicMock(status_code=200)
    client = _make_client()
    assert client.update_status("msg-123", "read") is True


@patch("openclaw_instagram.utils.iamq.httpx.get")
def test_get_agents(mock_get):
    """Lists registered agents."""
    mock_get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value=[
            {"id": "mail_agent", "last_heartbeat": 123},
            {"id": "test_agent", "last_heartbeat": 456},
        ]),
    )
    client = _make_client()
    agents = client.get_agents()
    assert len(agents) == 2


@patch("openclaw_instagram.utils.iamq.httpx.post")
def test_broadcast(mock_post):
    """Broadcast sends to 'broadcast' target."""
    mock_post.return_value = MagicMock(
        status_code=201,
        json=MagicMock(return_value={"id": "msg-789"}),
    )
    client = _make_client()
    client.broadcast("Test", "Body")
    payload = mock_post.call_args.kwargs["json"]
    assert payload["to"] == "broadcast"


@patch("openclaw_instagram.utils.iamq.httpx.post")
def test_announce_engagement(mock_post):
    """Engagement announcement broadcasts summary."""
    mock_post.return_value = MagicMock(
        status_code=201,
        json=MagicMock(return_value={"id": "msg-eng"}),
    )
    client = _make_client()
    results = {
        "user1": {"liked": 3, "errors": []},
        "user2": {"liked": 2, "errors": ["fail"]},
    }
    msg = client.announce_engagement(results)
    assert msg is not None
    payload = mock_post.call_args.kwargs["json"]
    assert "5 likes" in payload["subject"]
    assert "2 accounts" in payload["subject"]
    assert payload["to"] == "broadcast"


@patch("openclaw_instagram.utils.iamq.httpx.post")
def test_announce_error(mock_post):
    """Error announcement broadcasts with HIGH priority."""
    mock_post.return_value = MagicMock(
        status_code=201,
        json=MagicMock(return_value={"id": "msg-err"}),
    )
    client = _make_client()
    client.announce_error("login", "Connection refused")
    payload = mock_post.call_args.kwargs["json"]
    assert payload["priority"] == "HIGH"
    assert payload["type"] == "error"
    assert "login" in payload["subject"]


def test_start_stop_disabled():
    """Start/stop on disabled client is a no-op."""
    client = IAMQClient(enabled=False)
    client.start()  # Should not start thread
    assert client._heartbeat_thread is None
    client.stop()  # Should not error


@patch("openclaw_instagram.utils.iamq.httpx.post")
def test_start_registers_and_starts_heartbeat(mock_post):
    """Start registers and launches heartbeat thread."""
    mock_post.return_value = MagicMock(status_code=200)
    client = _make_client(heartbeat_interval=300)
    client.start()
    assert client._heartbeat_thread is not None
    assert client._heartbeat_thread.is_alive()
    client.stop()
    assert not client._heartbeat_thread.is_alive()
