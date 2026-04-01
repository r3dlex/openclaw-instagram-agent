"""Additional IAMQ tests for uncovered branches."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from openclaw_instagram.utils.iamq import IAMQClient


def _make_client(**overrides) -> IAMQClient:
    defaults = dict(
        base_url="http://localhost:18790",
        agent_id="test_agent",
        enabled=True,
    )
    defaults.update(overrides)
    return IAMQClient(**defaults)


# ---------------------------------------------------------------------------
# heartbeat error paths
# ---------------------------------------------------------------------------

@patch("openclaw_instagram.utils.iamq.httpx.post")
def test_heartbeat_failure_status(mock_post):
    """Heartbeat non-200 returns False."""
    mock_post.return_value = MagicMock(status_code=500)
    client = _make_client()
    assert client.heartbeat() is False


@patch("openclaw_instagram.utils.iamq.httpx.post")
def test_heartbeat_network_error(mock_post):
    """Heartbeat network error returns False."""
    mock_post.side_effect = httpx.ConnectError("Connection refused")
    client = _make_client()
    assert client.heartbeat() is False


# ---------------------------------------------------------------------------
# send error paths
# ---------------------------------------------------------------------------

@patch("openclaw_instagram.utils.iamq.httpx.post")
def test_send_failure_status(mock_post):
    """Send non-201 returns None."""
    mock_post.return_value = MagicMock(status_code=500, text="error")
    client = _make_client()
    result = client.send("other", "subject", "body")
    assert result is None


@patch("openclaw_instagram.utils.iamq.httpx.post")
def test_send_network_error(mock_post):
    """Send network error returns None."""
    mock_post.side_effect = httpx.ConnectError("Connection refused")
    client = _make_client()
    result = client.send("other", "subject", "body")
    assert result is None


@patch("openclaw_instagram.utils.iamq.httpx.post")
def test_send_with_expires_at(mock_post):
    """Send with expires_at includes it in payload."""
    mock_post.return_value = MagicMock(
        status_code=201,
        json=MagicMock(return_value={"id": "msg-exp"}),
    )
    client = _make_client()
    client.send("other", "sub", "body", expires_at="2026-01-01T00:00:00Z")
    payload = mock_post.call_args.kwargs["json"]
    assert payload["expiresAt"] == "2026-01-01T00:00:00Z"


# ---------------------------------------------------------------------------
# inbox error paths
# ---------------------------------------------------------------------------

@patch("openclaw_instagram.utils.iamq.httpx.get")
def test_inbox_failure_status(mock_get):
    """Inbox non-200 returns empty list."""
    mock_get.return_value = MagicMock(status_code=500)
    client = _make_client()
    assert client.inbox() == []


@patch("openclaw_instagram.utils.iamq.httpx.get")
def test_inbox_network_error(mock_get):
    """Inbox network error returns empty list."""
    mock_get.side_effect = httpx.ConnectError("Connection refused")
    client = _make_client()
    assert client.inbox() == []


@patch("openclaw_instagram.utils.iamq.httpx.get")
def test_inbox_no_status_filter(mock_get):
    """inbox(status=None) omits status param from request."""
    mock_get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value={"messages": []}),
    )
    client = _make_client()
    client.inbox(status=None)
    call_kwargs = mock_get.call_args.kwargs
    assert "params" in call_kwargs
    assert call_kwargs["params"] == {}


# ---------------------------------------------------------------------------
# update_status error paths
# ---------------------------------------------------------------------------

@patch("openclaw_instagram.utils.iamq.httpx.patch")
def test_update_status_failure(mock_patch):
    """update_status non-200 returns False."""
    mock_patch.return_value = MagicMock(status_code=404)
    client = _make_client()
    assert client.update_status("msg-123", "read") is False


@patch("openclaw_instagram.utils.iamq.httpx.patch")
def test_update_status_network_error(mock_patch):
    """update_status network error returns False."""
    mock_patch.side_effect = httpx.ConnectError("Connection refused")
    client = _make_client()
    assert client.update_status("msg-123", "read") is False


# ---------------------------------------------------------------------------
# get_agents error paths
# ---------------------------------------------------------------------------

@patch("openclaw_instagram.utils.iamq.httpx.get")
def test_get_agents_failure(mock_get):
    """get_agents non-200 returns empty list."""
    mock_get.return_value = MagicMock(status_code=500)
    client = _make_client()
    assert client.get_agents() == []


@patch("openclaw_instagram.utils.iamq.httpx.get")
def test_get_agents_network_error(mock_get):
    """get_agents network error returns empty list."""
    mock_get.side_effect = httpx.ConnectError("Connection refused")
    client = _make_client()
    assert client.get_agents() == []


@patch("openclaw_instagram.utils.iamq.httpx.get")
def test_get_agents_dict_format(mock_get):
    """get_agents handles {'agents': [...]} response format."""
    mock_get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value={"agents": [{"id": "a1"}], "total": 1}),
    )
    client = _make_client()
    result = client.get_agents()
    assert result == [{"id": "a1"}]


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------

@patch("openclaw_instagram.utils.iamq.httpx.get")
def test_get_status_success(mock_get):
    """get_status returns status dict."""
    mock_get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value={"queue_size": 5}),
    )
    client = _make_client()
    result = client.get_status()
    assert result == {"queue_size": 5}


@patch("openclaw_instagram.utils.iamq.httpx.get")
def test_get_status_failure(mock_get):
    """get_status non-200 returns None."""
    mock_get.return_value = MagicMock(status_code=503)
    client = _make_client()
    assert client.get_status() is None


@patch("openclaw_instagram.utils.iamq.httpx.get")
def test_get_status_network_error(mock_get):
    """get_status network error returns None."""
    mock_get.side_effect = httpx.ConnectError("Connection refused")
    client = _make_client()
    assert client.get_status() is None


# ---------------------------------------------------------------------------
# announce_api_cooldown
# ---------------------------------------------------------------------------

@patch("openclaw_instagram.utils.iamq.httpx.post")
def test_announce_api_cooldown(mock_post):
    """announce_api_cooldown broadcasts with cooldown hours in subject."""
    mock_post.return_value = MagicMock(
        status_code=201,
        json=MagicMock(return_value={"id": "msg-cooldown"}),
    )
    client = _make_client()
    client.announce_api_cooldown(hours=24)
    payload = mock_post.call_args.kwargs["json"]
    assert "24h" in payload["subject"]
    assert payload["to"] == "broadcast"


# ---------------------------------------------------------------------------
# metadata merging
# ---------------------------------------------------------------------------

def test_metadata_merge_uses_defaults():
    """IAMQClient merges caller metadata over defaults, preserving all keys."""
    client = IAMQClient(
        enabled=False,
        metadata={"name": "Custom Name", "extra_key": "extra_val"},
    )
    # Should have both the overridden name and default description
    assert client._metadata["name"] == "Custom Name"
    assert "description" in client._metadata
    assert client._metadata["extra_key"] == "extra_val"


def test_metadata_adds_workspace_if_missing():
    """IAMQClient adds workspace to metadata if not provided."""
    client = IAMQClient(enabled=False, metadata={})
    assert "workspace" in client._metadata


def test_metadata_does_not_override_workspace_if_set():
    """IAMQClient preserves workspace if already in metadata."""
    client = IAMQClient(enabled=False, metadata={"workspace": "/custom/path"})
    assert client._metadata["workspace"] == "/custom/path"


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

def test_enabled_property():
    """enabled property reflects constructor value."""
    assert IAMQClient(enabled=True).enabled is True
    assert IAMQClient(enabled=False).enabled is False


def test_agent_id_property():
    """agent_id property reflects constructor value."""
    client = IAMQClient(agent_id="my_agent", enabled=False)
    assert client.agent_id == "my_agent"
