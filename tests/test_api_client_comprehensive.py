"""Comprehensive tests for InstagramAPIClient."""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

from instagrapi.exceptions import (
    ChallengeRequired,
    LoginRequired,
    PleaseWaitFewMinutes,
    RateLimitError,
    TwoFactorRequired,
)

from openclaw_instagram.api.client import InstagramAPIClient
from openclaw_instagram.config import Settings


def _make_settings(**overrides) -> Settings:
    defaults = dict(
        instagram_username="test_user",
        instagram_password="test_pass",
        ig_2fa_seed="",
        max_actions_per_hour=100,
        min_action_delay_seconds=0,
        max_action_delay_seconds=0,
        api_retry_hours=24,
    )
    defaults.update(overrides)
    return Settings(**defaults)


# ---------------------------------------------------------------------------
# api_available — cooldown logic
# ---------------------------------------------------------------------------

def test_api_available_true_by_default(tmp_path):
    """API is available when no failure has been recorded."""
    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.API_FAILURE_FILE", tmp_path / "api_failure_timestamp"),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        api = InstagramAPIClient(_make_settings())
        assert api.api_available is True


def test_api_available_false_during_cooldown(tmp_path):
    """API is unavailable when failure file exists and cooldown hasn't expired."""
    failure_file = tmp_path / "api_failure_timestamp"
    failure_file.write_text(str(time.time()))  # failure just happened

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.API_FAILURE_FILE", failure_file),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
    ):
        api = InstagramAPIClient(_make_settings())
        api._api_available = False
        assert api.api_available is False


def test_api_available_true_after_cooldown_expires(tmp_path):
    """API becomes available again after cooldown expires."""
    failure_file = tmp_path / "api_failure_timestamp"
    # Record failure from 25 hours ago (beyond 24h retry)
    failure_file.write_text(str(time.time() - 90000))

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.API_FAILURE_FILE", failure_file),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
    ):
        api = InstagramAPIClient(_make_settings())
        api._api_available = False
        result = api.api_available
        assert result is True
        # Failure file should have been removed
        assert not failure_file.exists()


# ---------------------------------------------------------------------------
# _mark_api_failed
# ---------------------------------------------------------------------------

def test_mark_api_failed_creates_file(tmp_path):
    """_mark_api_failed writes timestamp file and sets _api_available=False."""
    failure_file = tmp_path / "api_failure_timestamp"
    mock_iamq = MagicMock()

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.API_FAILURE_FILE", failure_file),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
    ):
        api = InstagramAPIClient(_make_settings(), iamq_client=mock_iamq)
        api._mark_api_failed()

    assert failure_file.exists()
    assert api._api_available is False
    mock_iamq.announce_api_cooldown.assert_called_once()


def test_mark_api_failed_no_iamq(tmp_path):
    """_mark_api_failed works fine when no iamq client is set."""
    failure_file = tmp_path / "api_failure_timestamp"

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.API_FAILURE_FILE", failure_file),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
    ):
        api = InstagramAPIClient(_make_settings())
        api._mark_api_failed()

    assert failure_file.exists()
    assert api._api_available is False


# ---------------------------------------------------------------------------
# _get_client — session restore
# ---------------------------------------------------------------------------

@patch("openclaw_instagram.api.client.InstaClient")
def test_get_client_reuses_existing(mock_cls, tmp_path):
    """_get_client returns cached client on second call."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.get_settings.return_value = {}

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        api = InstagramAPIClient(_make_settings())
        c1 = api._get_client()
        c2 = api._get_client()

    assert c1 is c2
    assert mock_cls.call_count == 1


@patch("openclaw_instagram.api.client.InstaClient")
def test_get_client_restores_session(mock_cls, tmp_path):
    """_get_client loads existing session from disk."""
    session_file = tmp_path / "session.json"
    session_file.write_text(json.dumps({"key": "value"}))

    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.get_settings.return_value = {"key": "value"}

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.SESSION_FILE", session_file),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        api = InstagramAPIClient(_make_settings())
        client = api._get_client()

    assert client is mock_client
    mock_client.set_settings.assert_called_once_with({"key": "value"})


@patch("openclaw_instagram.api.client.InstaClient")
def test_get_client_session_restore_fails_then_fresh_login(mock_cls, tmp_path):
    """If session restore fails, falls back to fresh login."""
    session_file = tmp_path / "session.json"
    session_file.write_text(json.dumps({"key": "old"}))

    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.get_settings.return_value = {"key": "new"}
    # First login (session restore) raises, second (fresh login) succeeds
    mock_client.login.side_effect = [Exception("Session expired"), None]

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.SESSION_FILE", session_file),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        api = InstagramAPIClient(_make_settings())
        client = api._get_client()

    assert client is mock_client
    assert mock_client.login.call_count == 2


@patch("openclaw_instagram.api.client.InstaClient")
def test_get_client_session_restore_2fa_required(mock_cls, tmp_path):
    """If session restore requires 2FA, deletes session and does fresh login."""
    session_file = tmp_path / "session.json"
    session_file.write_text(json.dumps({"key": "old"}))

    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.get_settings.return_value = {}
    # First login (with session) raises TwoFactorRequired
    mock_client.login.side_effect = [TwoFactorRequired(), None]

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.SESSION_FILE", session_file),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        api = InstagramAPIClient(_make_settings())
        api._get_client()

    # Fresh login happened
    assert mock_client.login.call_count == 2


# ---------------------------------------------------------------------------
# _safe_call — error paths
# ---------------------------------------------------------------------------

@patch("openclaw_instagram.api.client.InstaClient")
def test_safe_call_rate_limit_error(mock_cls, tmp_path):
    """RateLimitError triggers _mark_api_failed and returns None."""
    failure_file = tmp_path / "api_failure_timestamp"
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.get_settings.return_value = {}
    mock_client.some_method = MagicMock(side_effect=RateLimitError("Rate limited"))

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
        patch("openclaw_instagram.api.client.API_FAILURE_FILE", failure_file),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        api = InstagramAPIClient(_make_settings())
        result = api._safe_call("some_method")

    assert result is None
    assert api._api_available is False


@patch("openclaw_instagram.api.client.InstaClient")
def test_safe_call_please_wait_error(mock_cls, tmp_path):
    """PleaseWaitFewMinutes triggers _mark_api_failed and returns None."""
    failure_file = tmp_path / "api_failure_timestamp"
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.get_settings.return_value = {}
    mock_client.some_method = MagicMock(side_effect=PleaseWaitFewMinutes("Wait"))

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
        patch("openclaw_instagram.api.client.API_FAILURE_FILE", failure_file),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        api = InstagramAPIClient(_make_settings())
        result = api._safe_call("some_method")

    assert result is None
    assert api._api_available is False


@patch("openclaw_instagram.api.client.InstaClient")
def test_safe_call_challenge_required(mock_cls, tmp_path):
    """ChallengeRequired triggers _mark_api_failed and returns None."""
    failure_file = tmp_path / "api_failure_timestamp"
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.get_settings.return_value = {}
    mock_client.some_method = MagicMock(side_effect=ChallengeRequired())

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
        patch("openclaw_instagram.api.client.API_FAILURE_FILE", failure_file),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        api = InstagramAPIClient(_make_settings())
        result = api._safe_call("some_method")

    assert result is None
    assert api._api_available is False


@patch("openclaw_instagram.api.client.InstaClient")
def test_safe_call_login_required_relogins(mock_cls, tmp_path):
    """LoginRequired triggers re-login and retries the call."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.get_settings.return_value = {}
    # First call: LoginRequired; second call (after re-login): success
    mock_client.some_method = MagicMock(side_effect=[LoginRequired(), "success"])

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
        patch("openclaw_instagram.api.client.API_FAILURE_FILE", tmp_path / "api_failure"),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        api = InstagramAPIClient(_make_settings())
        result = api._safe_call("some_method")

    assert result == "success"


@patch("openclaw_instagram.api.client.InstaClient")
def test_safe_call_login_required_relogin_fails(mock_cls, tmp_path):
    """LoginRequired relogin failure marks API failed and returns None."""
    failure_file = tmp_path / "api_failure_timestamp"
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.get_settings.return_value = {}

    # Initial login (fresh) succeeds so _get_client returns client.
    # Then some_method triggers LoginRequired; re-login then fails.
    mock_client.login.side_effect = [None, Exception("Login completely failed")]
    mock_client.some_method = MagicMock(side_effect=LoginRequired())

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
        patch("openclaw_instagram.api.client.API_FAILURE_FILE", failure_file),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        api = InstagramAPIClient(_make_settings())
        result = api._safe_call("some_method")

    assert result is None
    assert api._api_available is False


@patch("openclaw_instagram.api.client.InstaClient")
def test_safe_call_generic_exception(mock_cls, tmp_path):
    """Generic exceptions return None without marking API failed."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.get_settings.return_value = {}
    mock_client.some_method = MagicMock(side_effect=ValueError("Unexpected"))

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
        patch("openclaw_instagram.api.client.API_FAILURE_FILE", tmp_path / "api_fail"),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        api = InstagramAPIClient(_make_settings())
        result = api._safe_call("some_method")

    assert result is None
    # API should still be available (only rate/challenge marks it failed)
    assert api._api_available is True


@patch("openclaw_instagram.api.client.InstaClient")
def test_safe_call_rate_limited(mock_cls, tmp_path):
    """_safe_call returns None when rate limiter says no more actions."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        api = InstagramAPIClient(_make_settings(max_actions_per_hour=0))
        result = api._safe_call("some_method")

    assert result is None


# ---------------------------------------------------------------------------
# Public engagement methods
# ---------------------------------------------------------------------------

@patch("openclaw_instagram.api.client.InstaClient")
def test_get_user_id(mock_cls, tmp_path):
    """get_user_id wraps _safe_call and converts to int."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.get_settings.return_value = {}
    mock_client.user_id_from_username = MagicMock(return_value=12345)

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
        patch("openclaw_instagram.api.client.API_FAILURE_FILE", tmp_path / "f"),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        api = InstagramAPIClient(_make_settings())
        result = api.get_user_id("testuser")

    assert result == 12345


@patch("openclaw_instagram.api.client.InstaClient")
def test_get_user_id_returns_none_on_failure(mock_cls, tmp_path):
    """get_user_id returns None when safe_call returns None."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.get_settings.return_value = {}
    mock_client.user_id_from_username = MagicMock(side_effect=ValueError("not found"))

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
        patch("openclaw_instagram.api.client.API_FAILURE_FILE", tmp_path / "f"),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        api = InstagramAPIClient(_make_settings())
        result = api.get_user_id("nobody")

    assert result is None


@patch("openclaw_instagram.api.client.InstaClient")
def test_get_user_medias(mock_cls, tmp_path):
    """get_user_medias returns list of media objects."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.get_settings.return_value = {}
    mock_client.user_medias = MagicMock(return_value=["media1", "media2"])

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
        patch("openclaw_instagram.api.client.API_FAILURE_FILE", tmp_path / "f"),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        api = InstagramAPIClient(_make_settings())
        result = api.get_user_medias(12345, count=5)

    assert result == ["media1", "media2"]


@patch("openclaw_instagram.api.client.InstaClient")
def test_get_user_medias_returns_empty_on_none(mock_cls, tmp_path):
    """get_user_medias returns [] when safe_call returns None."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.get_settings.return_value = {}
    mock_client.user_medias = MagicMock(side_effect=ValueError("err"))

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
        patch("openclaw_instagram.api.client.API_FAILURE_FILE", tmp_path / "f"),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        api = InstagramAPIClient(_make_settings())
        result = api.get_user_medias(12345)

    assert result == []


@patch("openclaw_instagram.api.client.InstaClient")
def test_like_media_success(mock_cls, tmp_path):
    """like_media returns True when API call succeeds."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.get_settings.return_value = {}
    mock_client.media_like = MagicMock(return_value=True)

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
        patch("openclaw_instagram.api.client.API_FAILURE_FILE", tmp_path / "f"),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        api = InstagramAPIClient(_make_settings())
        result = api.like_media("media_123")

    assert result is True


@patch("openclaw_instagram.api.client.InstaClient")
def test_like_media_failure(mock_cls, tmp_path):
    """like_media returns False when API call fails."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.get_settings.return_value = {}
    mock_client.media_like = MagicMock(side_effect=ValueError("failed"))

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
        patch("openclaw_instagram.api.client.API_FAILURE_FILE", tmp_path / "f"),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        api = InstagramAPIClient(_make_settings())
        result = api.like_media("media_123")

    assert result is False


@patch("openclaw_instagram.api.client.InstaClient")
def test_get_direct_threads(mock_cls, tmp_path):
    """get_direct_threads returns list of threads."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.get_settings.return_value = {}
    mock_client.direct_threads = MagicMock(return_value=["thread1"])

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
        patch("openclaw_instagram.api.client.API_FAILURE_FILE", tmp_path / "f"),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        api = InstagramAPIClient(_make_settings())
        result = api.get_direct_threads()

    assert result == ["thread1"]


@patch("openclaw_instagram.api.client.InstaClient")
def test_get_direct_messages(mock_cls, tmp_path):
    """get_direct_messages returns list of messages."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.get_settings.return_value = {}
    mock_client.direct_messages = MagicMock(return_value=["msg1", "msg2"])

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
        patch("openclaw_instagram.api.client.API_FAILURE_FILE", tmp_path / "f"),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        api = InstagramAPIClient(_make_settings())
        result = api.get_direct_messages(123)

    assert result == ["msg1", "msg2"]


@patch("openclaw_instagram.api.client.InstaClient")
def test_get_user_stories(mock_cls, tmp_path):
    """get_user_stories returns list of stories."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.get_settings.return_value = {}
    mock_client.user_stories = MagicMock(return_value=["story1"])

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
        patch("openclaw_instagram.api.client.API_FAILURE_FILE", tmp_path / "f"),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        api = InstagramAPIClient(_make_settings())
        result = api.get_user_stories(12345)

    assert result == ["story1"]


# ---------------------------------------------------------------------------
# Liked/commented cache methods
# ---------------------------------------------------------------------------

def test_get_liked_posts_empty(tmp_path):
    """get_liked_posts returns empty set when cache doesn't exist."""
    liked_file = tmp_path / "liked_posts.json"

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.LIKED_CACHE_FILE", liked_file),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
    ):
        api = InstagramAPIClient(_make_settings())
        result = api.get_liked_posts()

    assert result == set()


def test_get_liked_posts_reads_cache(tmp_path):
    """get_liked_posts reads existing cache file."""
    liked_file = tmp_path / "liked_posts.json"
    liked_file.write_text(json.dumps(["post1", "post2"]))

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.LIKED_CACHE_FILE", liked_file),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
    ):
        api = InstagramAPIClient(_make_settings())
        result = api.get_liked_posts()

    assert result == {"post1", "post2"}


def test_mark_liked(tmp_path):
    """mark_liked adds a post PK to the liked cache."""
    liked_file = tmp_path / "liked_posts.json"

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.LIKED_CACHE_FILE", liked_file),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
    ):
        api = InstagramAPIClient(_make_settings())
        api.mark_liked("post_abc")
        api.mark_liked("post_xyz")
        result = api.get_liked_posts()

    assert "post_abc" in result
    assert "post_xyz" in result


def test_get_commented_posts_empty(tmp_path):
    """get_commented_posts returns empty set when cache doesn't exist."""
    commented_file = tmp_path / "commented_posts.json"

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.COMMENTED_CACHE_FILE", commented_file),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
    ):
        api = InstagramAPIClient(_make_settings())
        result = api.get_commented_posts()

    assert result == set()


def test_mark_commented(tmp_path):
    """mark_commented adds a post PK to the commented cache."""
    commented_file = tmp_path / "commented_posts.json"

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.COMMENTED_CACHE_FILE", commented_file),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
    ):
        api = InstagramAPIClient(_make_settings())
        api.mark_commented("post_123")
        result = api.get_commented_posts()

    assert "post_123" in result


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------

@patch("openclaw_instagram.api.client.InstaClient")
def test_close_saves_session(mock_cls, tmp_path):
    """close() writes the session file."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.get_settings.return_value = {"key": "value"}
    session_file = tmp_path / "session.json"

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.SESSION_FILE", session_file),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        api = InstagramAPIClient(_make_settings())
        api._get_client()  # Initialize client
        api.close()

    assert api._client is None


def test_close_without_client(tmp_path):
    """close() without a client doesn't raise."""
    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.SESSION_FILE", tmp_path / "session.json"),
    ):
        api = InstagramAPIClient(_make_settings())
        api.close()  # Should not raise

    assert api._client is None


# ---------------------------------------------------------------------------
# _save_session
# ---------------------------------------------------------------------------

@patch("openclaw_instagram.api.client.InstaClient")
def test_save_session(mock_cls, tmp_path):
    """_save_session writes current settings to file."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.get_settings.return_value = {"session": "data"}
    session_file = tmp_path / "session.json"

    with (
        patch("openclaw_instagram.api.client.SESSION_CACHE_DIR", tmp_path),
        patch("openclaw_instagram.api.client.SESSION_FILE", session_file),
        patch("openclaw_instagram.api.client.sleep_human", return_value=0.0),
    ):
        api = InstagramAPIClient(_make_settings())
        api._get_client()
        api._save_session()

    assert session_file.exists()
    saved = json.loads(session_file.read_text())
    assert saved == {"session": "data"}
