"""Comprehensive tests for InstagramAgent orchestration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
        iamq_enabled=False,
    )
    defaults.update(overrides)
    return Settings(**defaults)


def _make_media(pk: str, media_type: int = 1, caption: str = "") -> MagicMock:
    """Create a mock media object."""
    m = MagicMock()
    m.pk = pk
    m.id = pk
    m.media_type = media_type
    m.caption_text = caption
    return m


def _make_agent(settings, mock_api, mock_browser):
    """Helper to create agent with mocked internals."""
    with (
        patch("openclaw_instagram.agent.setup_logging"),
        patch("openclaw_instagram.agent.InstagramAPIClient", return_value=mock_api),
        patch("openclaw_instagram.agent.BrowserFallback", return_value=mock_browser),
        patch("openclaw_instagram.agent.IAMQClient") as mock_iamq_cls,
    ):
        mock_iamq = MagicMock()
        mock_iamq.enabled = False
        mock_iamq_cls.return_value = mock_iamq
        agent = InstagramAgent(settings)
        return agent


# ---------------------------------------------------------------------------
# engage_accounts — API path
# ---------------------------------------------------------------------------

@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_engage_accounts_api_skips_already_liked(mock_browser_cls, mock_api_cls, mock_log):
    """Posts already in liked cache are skipped."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api.api_available = True
    mock_api.get_user_id.return_value = 1
    media = _make_media("post_100")
    mock_api.get_user_medias.return_value = [media]
    mock_api.get_liked_posts.return_value = {"post_100"}
    mock_api.get_commented_posts.return_value = set()
    mock_api_cls.return_value = mock_api

    agent = InstagramAgent(settings)
    result = agent.engage_accounts(["user1"])

    assert result["user1"]["skipped"] == 1
    assert result["user1"]["liked"] == 0
    mock_api.like_media.assert_not_called()


@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_engage_accounts_api_likes_new_post(mock_browser_cls, mock_api_cls, mock_log):
    """New photo post is liked."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api.api_available = True
    mock_api.get_user_id.return_value = 1
    media = _make_media("post_200", media_type=1)
    mock_api.get_user_medias.return_value = [media]
    mock_api.get_liked_posts.return_value = set()
    mock_api.get_commented_posts.return_value = set()
    mock_api.like_media.return_value = True
    mock_api_cls.return_value = mock_api

    agent = InstagramAgent(settings)
    result = agent.engage_accounts(["user1"])

    assert result["user1"]["liked"] == 1
    mock_api.like_media.assert_called_once_with("post_200")
    mock_api.mark_liked.assert_called_once_with("post_200")


@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_engage_accounts_api_comments_on_reel(mock_browser_cls, mock_api_cls, mock_log):
    """New reel gets a comment for known username."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api.api_available = True
    mock_api.get_user_id.return_value = 1
    media = _make_media("reel_300", media_type=2, caption="restaurant in stuttgart")
    mock_api.get_user_medias.return_value = [media]
    mock_api.get_liked_posts.return_value = set()
    mock_api.get_commented_posts.return_value = set()
    mock_api.like_media.return_value = True
    mock_api_cls.return_value = mock_api

    agent = InstagramAgent(settings)
    result = agent.engage_accounts(["stuttgart_blog"])

    assert result["stuttgart_blog"]["commented"] == 1
    mock_api.media_comment.assert_called_once()
    mock_api.mark_commented.assert_called_once_with("reel_300")


@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_engage_accounts_api_comment_exception(mock_browser_cls, mock_api_cls, mock_log):
    """Exception during comment is caught and logged, not re-raised."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api.api_available = True
    mock_api.get_user_id.return_value = 1
    media = _make_media("reel_400", media_type=2, caption="stuttgart west restaurant")
    mock_api.get_user_medias.return_value = [media]
    mock_api.get_liked_posts.return_value = set()
    mock_api.get_commented_posts.return_value = set()
    mock_api.like_media.return_value = True
    mock_api.media_comment.side_effect = Exception("Comment API error")
    mock_api_cls.return_value = mock_api

    agent = InstagramAgent(settings)
    result = agent.engage_accounts(["stuttgart_blog"])

    # liked but commented count stays at 0 due to exception
    assert result["stuttgart_blog"]["liked"] == 1
    assert result["stuttgart_blog"]["commented"] == 0


@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_engage_accounts_api_user_not_found(mock_browser_cls, mock_api_cls, mock_log):
    """When user ID cannot be resolved, an error is recorded."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api.api_available = True
    mock_api.get_user_id.return_value = None
    mock_api_cls.return_value = mock_api

    agent = InstagramAgent(settings)
    result = agent.engage_accounts(["unknown_user"])

    assert len(result["unknown_user"]["errors"]) == 1
    assert "Could not resolve user" in result["unknown_user"]["errors"][0]


@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_engage_accounts_api_like_fails(mock_browser_cls, mock_api_cls, mock_log):
    """When like_media returns False, liked count stays at 0."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api.api_available = True
    mock_api.get_user_id.return_value = 1
    media = _make_media("post_500")
    mock_api.get_user_medias.return_value = [media]
    mock_api.get_liked_posts.return_value = set()
    mock_api.get_commented_posts.return_value = set()
    mock_api.like_media.return_value = False
    mock_api_cls.return_value = mock_api

    agent = InstagramAgent(settings)
    result = agent.engage_accounts(["user1"])

    assert result["user1"]["liked"] == 0
    mock_api.mark_liked.assert_not_called()


@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_engage_accounts_multiple_users(mock_browser_cls, mock_api_cls, mock_log):
    """Engagement runs for each username in the list."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api.api_available = True
    mock_api.get_user_id.side_effect = [1, 2]
    mock_api.get_user_medias.return_value = []
    mock_api.get_liked_posts.return_value = set()
    mock_api.get_commented_posts.return_value = set()
    mock_api_cls.return_value = mock_api

    agent = InstagramAgent(settings)
    result = agent.engage_accounts(["user1", "user2"])

    assert "user1" in result
    assert "user2" in result
    assert mock_api.get_user_id.call_count == 2


# ---------------------------------------------------------------------------
# _generate_comment — various username/caption combos
# ---------------------------------------------------------------------------

@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_generate_comment_stuttgart_blog_various(mock_browser_cls, mock_api_cls, mock_log):
    """_generate_comment returns German comments for stuttgart_blog captions."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api_cls.return_value = mock_api
    agent = InstagramAgent(settings)

    # Test various trigger words
    assert agent._generate_comment("stuttgart_blog", "magnolien in der wilhelma", "Video/Reel") is not None
    assert agent._generate_comment("stuttgart_blog", "stuttgart 21 tunnel", "Video/Reel") is not None
    assert agent._generate_comment("stuttgart_blog", "business portrait foto", "Video/Reel") is not None
    assert agent._generate_comment("stuttgart_blog", "terrasse sonnenterrasse", "Video/Reel") is not None
    assert agent._generate_comment("stuttgart_blog", "indoor spielplatz kinder", "Video/Reel") is not None
    assert agent._generate_comment("stuttgart_blog", "artbeat malen kreativ", "Video/Reel") is not None
    assert agent._generate_comment("stuttgart_blog", "Mauritius beach urlaub", "Video/Reel") is not None
    assert agent._generate_comment("stuttgart_blog", "perlen schmuck studio", "Video/Reel") is not None
    assert agent._generate_comment("stuttgart_blog", "pizza pasta restaurant", "Video/Reel") is not None
    assert agent._generate_comment("stuttgart_blog", "workshop frauenpower", "Video/Reel") is not None
    assert agent._generate_comment("stuttgart_blog", "abnehmen fitness gesund", "Video/Reel") is not None
    assert agent._generate_comment("stuttgart_blog", "gewinnspiel geschenk", "Video/Reel") is not None
    # Default comment
    default = agent._generate_comment("stuttgart_blog", "something random unrelated", "Video/Reel")
    assert default == "Super Beitrag! 👏"


@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_generate_comment_stuttgartmitkind_various(mock_browser_cls, mock_api_cls, mock_log):
    """_generate_comment returns German comments for stuttgartmitkind captions."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api_cls.return_value = mock_api
    agent = InstagramAgent(settings)

    assert agent._generate_comment("stuttgartmitkind", "artbeat malen kreativ gemalt", "Video/Reel") is not None
    assert agent._generate_comment("stuttgartmitkind", "mauritius spiel spaß", "Video/Reel") is not None
    assert agent._generate_comment("stuttgartmitkind", "indoor spielplatz innenstadt", "Video/Reel") is not None
    assert agent._generate_comment("stuttgartmitkind", "buildabearde kuscheltier teddy", "Video/Reel") is not None
    assert agent._generate_comment("stuttgartmitkind", "spielzeug testen monat", "Video/Reel") is not None
    assert agent._generate_comment("stuttgartmitkind", " crêpes workshop kochen", "Video/Reel") is not None
    assert agent._generate_comment("stuttgartmitkind", "weihnachtsmarkt glühwein", "Video/Reel") is not None
    assert agent._generate_comment("stuttgartmitkind", "kinder perspektive nicky entdeckt", "Video/Reel") is not None
    assert agent._generate_comment("stuttgartmitkind", " Indoor hüpfburg ritts", "Video/Reel") is not None
    assert agent._generate_comment("stuttgartmitkind", "werbung anzeige", "Video/Reel") is not None
    # Default
    default = agent._generate_comment("stuttgartmitkind", "something else", "Video/Reel")
    assert "Nicky" in default


@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_generate_comment_ankes_insta_various(mock_browser_cls, mock_api_cls, mock_log):
    """_generate_comment returns comments for ankes_insta captions."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api_cls.return_value = mock_api
    agent = InstagramAgent(settings)

    assert agent._generate_comment("ankes_insta", "love relationship paar", "Video/Reel") is not None
    assert agent._generate_comment("ankes_insta", "floriano baby newborn", "Video/Reel") is not None
    assert agent._generate_comment("ankes_insta", "greece griechenland sommer", "Video/Reel") is not None
    assert agent._generate_comment("ankes_insta", "turkey extended summer türkei", "Video/Reel") is not None
    assert agent._generate_comment("ankes_insta", "colorfully languages greeting", "Video/Reel") is not None
    assert agent._generate_comment("ankes_insta", "podcast where are they now", "Video/Reel") is not None
    # floriano fallback (without other keywords)
    result = agent._generate_comment("ankes_insta", "floriano", "Video/Reel")
    assert result is not None
    # Default
    default = agent._generate_comment("ankes_insta", "something else entirely", "Video/Reel")
    assert default == "Beautiful content! 💕"


@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_generate_comment_unknown_username_returns_none(mock_browser_cls, mock_api_cls, mock_log):
    """Unknown username returns None."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api_cls.return_value = mock_api
    agent = InstagramAgent(settings)

    result = agent._generate_comment("some_random_user", "anything", "Video/Reel")
    assert result is None


# ---------------------------------------------------------------------------
# check_dms
# ---------------------------------------------------------------------------

@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_check_dms_via_api(mock_browser_cls, mock_api_cls, mock_log):
    """check_dms returns structured messages when API is available."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api.api_available = True

    thread = MagicMock()
    thread.id = "thread_1"
    user = MagicMock()
    user.username = "user1"
    thread.users = [user]
    mock_api.get_direct_threads.return_value = [thread]
    mock_api_cls.return_value = mock_api

    agent = InstagramAgent(settings)
    messages = agent.check_dms(filter_usernames=["user1"])

    assert len(messages) == 1
    assert messages[0]["username"] == "user1"
    assert messages[0]["source"] == "api"


@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_check_dms_filters_usernames(mock_browser_cls, mock_api_cls, mock_log):
    """check_dms filters by username when filter_usernames is provided."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api.api_available = True

    thread1 = MagicMock()
    thread1.id = "t1"
    user1 = MagicMock()
    user1.username = "allowed_user"
    thread1.users = [user1]

    thread2 = MagicMock()
    thread2.id = "t2"
    user2 = MagicMock()
    user2.username = "other_user"
    thread2.users = [user2]

    mock_api.get_direct_threads.return_value = [thread1, thread2]
    mock_api_cls.return_value = mock_api

    agent = InstagramAgent(settings)
    messages = agent.check_dms(filter_usernames=["allowed_user"])

    assert len(messages) == 1
    assert messages[0]["username"] == "allowed_user"


@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_check_dms_no_filter(mock_browser_cls, mock_api_cls, mock_log):
    """check_dms without filter returns all threads."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api.api_available = True

    thread = MagicMock()
    thread.id = "t1"
    user = MagicMock()
    user.username = "anyone"
    thread.users = [user]
    mock_api.get_direct_threads.return_value = [thread]
    mock_api_cls.return_value = mock_api

    agent = InstagramAgent(settings)
    messages = agent.check_dms(filter_usernames=None)

    assert len(messages) == 1


@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_check_dms_via_browser(mock_browser_cls, mock_api_cls, mock_log):
    """check_dms falls back to browser when API unavailable."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api.api_available = False
    mock_api_cls.return_value = mock_api

    mock_browser = MagicMock()

    async def fake_check_dms():
        return [{"sender": "user1", "preview": "Hey!"}]

    mock_browser.check_dms = fake_check_dms
    mock_browser_cls.return_value = mock_browser

    agent = InstagramAgent(settings)
    messages = agent.check_dms(filter_usernames=["user1"])

    assert len(messages) == 1
    assert messages[0]["username"] == "user1"
    assert messages[0]["source"] == "browser"


@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_check_dms_via_browser_with_filter(mock_browser_cls, mock_api_cls, mock_log):
    """check_dms via browser respects filter_usernames."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api.api_available = False
    mock_api_cls.return_value = mock_api

    mock_browser = MagicMock()

    async def fake_check_dms():
        return [
            {"sender": "user1", "preview": "Hi"},
            {"sender": "other", "preview": "Hello"},
        ]

    mock_browser.check_dms = fake_check_dms
    mock_browser_cls.return_value = mock_browser

    agent = InstagramAgent(settings)
    messages = agent.check_dms(filter_usernames=["user1"])

    assert len(messages) == 1
    assert messages[0]["username"] == "user1"


# ---------------------------------------------------------------------------
# poll_iamq / get_peer_agents
# ---------------------------------------------------------------------------

@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_poll_iamq(mock_browser_cls, mock_api_cls, mock_log):
    """poll_iamq delegates to iamq.inbox."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api_cls.return_value = mock_api

    agent = InstagramAgent(settings)
    agent.iamq.inbox = MagicMock(return_value=[{"id": "m1"}])
    result = agent.poll_iamq()

    assert result == [{"id": "m1"}]
    agent.iamq.inbox.assert_called_once_with(status="unread")


@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_get_peer_agents(mock_browser_cls, mock_api_cls, mock_log):
    """get_peer_agents delegates to iamq.get_agents."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api_cls.return_value = mock_api

    agent = InstagramAgent(settings)
    agent.iamq.get_agents = MagicMock(return_value=[{"id": "mail_agent"}])
    result = agent.get_peer_agents()

    assert result == [{"id": "mail_agent"}]


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------

@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_close(mock_browser_cls, mock_api_cls, mock_log):
    """close() stops iamq, closes api, and closes browser."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api_cls.return_value = mock_api

    mock_browser = MagicMock()

    async def fake_close():
        pass

    mock_browser.close = fake_close
    mock_browser_cls.return_value = mock_browser

    agent = InstagramAgent(settings)
    # Replace iamq with a full mock so we can assert on stop
    mock_iamq = MagicMock()
    agent.iamq = mock_iamq
    agent.close()

    mock_iamq.stop.assert_called_once()
    mock_api.close.assert_called_once()


# ---------------------------------------------------------------------------
# _engage_via_browser error path
# ---------------------------------------------------------------------------

@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_engage_via_browser_error(mock_browser_cls, mock_api_cls, mock_log):
    """Browser engagement errors are caught and recorded."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api.api_available = False
    mock_api_cls.return_value = mock_api

    mock_browser = MagicMock()

    async def fake_like(username, count=3):
        raise Exception("Browser crashed")

    mock_browser.like_latest_posts = fake_like
    mock_browser_cls.return_value = mock_browser

    agent = InstagramAgent(settings)
    result = agent.engage_accounts(["user1"])

    assert result["user1"]["method"] == "browser"
    assert result["user1"]["liked"] == 0
    assert len(result["user1"]["errors"]) == 1
    assert "Browser crashed" in result["user1"]["errors"][0]


# ---------------------------------------------------------------------------
# media type handling
# ---------------------------------------------------------------------------

@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_engage_album_media_type(mock_browser_cls, mock_api_cls, mock_log):
    """Album (type=8) posts are liked but not commented."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api.api_available = True
    mock_api.get_user_id.return_value = 1
    media = _make_media("album_600", media_type=8, caption="album content")
    mock_api.get_user_medias.return_value = [media]
    mock_api.get_liked_posts.return_value = set()
    mock_api.get_commented_posts.return_value = set()
    mock_api.like_media.return_value = True
    mock_api_cls.return_value = mock_api

    agent = InstagramAgent(settings)
    result = agent.engage_accounts(["user1"])

    assert result["user1"]["liked"] == 1
    assert result["user1"]["commented"] == 0


@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_engage_unknown_media_type(mock_browser_cls, mock_api_cls, mock_log):
    """Unknown media type (e.g., 99) falls through gracefully."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api.api_available = True
    mock_api.get_user_id.return_value = 1
    media = _make_media("unknown_700", media_type=99, caption="")
    mock_api.get_user_medias.return_value = [media]
    mock_api.get_liked_posts.return_value = set()
    mock_api.get_commented_posts.return_value = set()
    mock_api.like_media.return_value = True
    mock_api_cls.return_value = mock_api

    agent = InstagramAgent(settings)
    result = agent.engage_accounts(["user1"])

    # Should not raise; liked count is correct
    assert result["user1"]["liked"] == 1


@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_engage_reel_already_commented(mock_browser_cls, mock_api_cls, mock_log):
    """Reels already commented are not commented again."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api.api_available = True
    mock_api.get_user_id.return_value = 1
    media = _make_media("reel_800", media_type=2, caption="stuttgart restaurant food")
    mock_api.get_user_medias.return_value = [media]
    mock_api.get_liked_posts.return_value = set()
    mock_api.get_commented_posts.return_value = {"reel_800"}  # already commented
    mock_api.like_media.return_value = True
    mock_api_cls.return_value = mock_api

    agent = InstagramAgent(settings)
    result = agent.engage_accounts(["stuttgart_blog"])

    # Liked but not commented again
    assert result["stuttgart_blog"]["liked"] == 1
    assert result["stuttgart_blog"]["commented"] == 0
    mock_api.media_comment.assert_not_called()


@patch("openclaw_instagram.agent.setup_logging")
@patch("openclaw_instagram.agent.InstagramAPIClient")
@patch("openclaw_instagram.agent.BrowserFallback")
def test_engage_no_caption_fallback(mock_browser_cls, mock_api_cls, mock_log):
    """Post with no caption still builds a summary."""
    settings = _make_settings()
    mock_api = MagicMock()
    mock_api.api_available = True
    mock_api.get_user_id.return_value = 1
    media = _make_media("post_900", media_type=1, caption="")
    media.caption_text = None  # no caption
    mock_api.get_user_medias.return_value = [media]
    mock_api.get_liked_posts.return_value = set()
    mock_api.get_commented_posts.return_value = set()
    mock_api.like_media.return_value = True
    mock_api_cls.return_value = mock_api

    agent = InstagramAgent(settings)
    result = agent.engage_accounts(["user1"])

    assert result["user1"]["liked"] == 1
    # Post summary should just be the media type
    assert result["user1"]["posts"][0]["summary"] == "Photo"
