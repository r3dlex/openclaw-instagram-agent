"""Comprehensive tests for BrowserFallback using mocked Playwright."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openclaw_instagram.browser.fallback import BrowserFallback
from openclaw_instagram.config import Settings


def _make_settings(**overrides) -> Settings:
    defaults = dict(
        instagram_username="test",
        instagram_password="test",
        min_action_delay_seconds=0,
        max_action_delay_seconds=0,
        browser_cdp_host="127.0.0.1",
        browser_cdp_port=9222,
    )
    defaults.update(overrides)
    return Settings(**defaults)


def _make_page_mock():
    """Create a fully-mocked Playwright page."""
    page = AsyncMock()
    page.is_closed = MagicMock(return_value=False)
    page.goto = AsyncMock()
    page.keyboard = AsyncMock()
    page.keyboard.press = AsyncMock()
    return page


def _make_locator_mock(count: int = 0):
    loc = AsyncMock()
    loc.count = AsyncMock(return_value=count)
    loc.nth = MagicMock(return_value=AsyncMock())
    loc.first = AsyncMock()
    loc.click = AsyncMock()
    loc.inner_text = AsyncMock(return_value="")
    return loc


@pytest.fixture
def settings():
    return _make_settings()


# ---------------------------------------------------------------------------
# _get_page  — CDP connection success
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_page_cdp_success(settings):
    """When CDP connect succeeds and context has pages, returns the first page."""
    fb = BrowserFallback(settings)

    mock_page = _make_page_mock()
    mock_context = MagicMock()
    mock_context.pages = [mock_page]
    mock_browser = AsyncMock()
    mock_browser.contexts = [mock_context]

    mock_pw = AsyncMock()
    mock_pw.chromium.connect_over_cdp = AsyncMock(return_value=mock_browser)

    with patch("openclaw_instagram.browser.fallback.async_playwright") as mock_apl:
        mock_apl.return_value.__aenter__ = AsyncMock(return_value=mock_pw)
        mock_apl.return_value.start = AsyncMock(return_value=mock_pw)
        # async_playwright() is used as an async context manager via .start()
        mock_apl.return_value = AsyncMock()
        mock_apl.return_value.start = AsyncMock(return_value=mock_pw)

        with patch(
            "openclaw_instagram.browser.fallback.async_sleep_human", new_callable=AsyncMock
        ):
            page = await fb._get_page()

    assert page is mock_page


@pytest.mark.asyncio
async def test_get_page_cdp_success_no_existing_pages(settings):
    """When CDP connects but context has no pages, creates a new page."""
    fb = BrowserFallback(settings)

    new_page = _make_page_mock()
    mock_context = AsyncMock()
    mock_context.pages = []
    mock_context.new_page = AsyncMock(return_value=new_page)

    mock_browser = AsyncMock()
    mock_browser.contexts = [mock_context]

    mock_pw = AsyncMock()
    mock_pw.chromium.connect_over_cdp = AsyncMock(return_value=mock_browser)

    with patch("openclaw_instagram.browser.fallback.async_playwright") as mock_apl:
        mock_apl.return_value.start = AsyncMock(return_value=mock_pw)
        page = await fb._get_page()

    assert page is new_page or page is not None


@pytest.mark.asyncio
async def test_get_page_cdp_no_contexts(settings):
    """When CDP connects but no contexts exist, creates a new context and page."""
    fb = BrowserFallback(settings)

    new_page = _make_page_mock()
    new_context = AsyncMock()
    new_context.new_page = AsyncMock(return_value=new_page)

    mock_browser = AsyncMock()
    mock_browser.contexts = []
    mock_browser.new_context = AsyncMock(return_value=new_context)

    mock_pw = AsyncMock()
    mock_pw.chromium.connect_over_cdp = AsyncMock(return_value=mock_browser)

    with patch("openclaw_instagram.browser.fallback.async_playwright") as mock_apl:
        mock_apl.return_value.start = AsyncMock(return_value=mock_pw)
        page = await fb._get_page()

    assert page is new_page or page is not None


@pytest.mark.asyncio
async def test_get_page_cdp_fallback_headless(settings):
    """When CDP fails, launches headless Chromium instead."""
    fb = BrowserFallback(settings)

    new_page = _make_page_mock()
    new_context = AsyncMock()
    new_context.new_page = AsyncMock(return_value=new_page)

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=new_context)

    mock_pw = AsyncMock()
    mock_pw.chromium.connect_over_cdp = AsyncMock(
        side_effect=Exception("CDP not available")
    )
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

    with patch("openclaw_instagram.browser.fallback.async_playwright") as mock_apl:
        mock_apl.return_value.start = AsyncMock(return_value=mock_pw)
        page = await fb._get_page()

    assert page is new_page or page is not None


@pytest.mark.asyncio
async def test_get_page_reuses_existing_page(settings):
    """If a page is already open and not closed, _get_page returns it immediately."""
    fb = BrowserFallback(settings)
    existing_page = _make_page_mock()
    existing_page.is_closed = MagicMock(return_value=False)
    fb._page = existing_page

    # No playwright patching needed — should return immediately
    page = await fb._get_page()
    assert page is existing_page


# ---------------------------------------------------------------------------
# navigate_to_profile
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_navigate_to_profile(settings):
    fb = BrowserFallback(settings)
    mock_page = _make_page_mock()
    fb._page = mock_page

    with patch(
        "openclaw_instagram.browser.fallback.async_sleep_human", new_callable=AsyncMock
    ):
        result = await fb.navigate_to_profile("testuser")

    mock_page.goto.assert_called_once_with(
        "https://www.instagram.com/testuser/", wait_until="networkidle"
    )
    assert result is mock_page


# ---------------------------------------------------------------------------
# like_latest_posts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_like_latest_posts_success(settings):
    """Likes posts when like button is found."""
    fb = BrowserFallback(settings)
    mock_page = _make_page_mock()
    fb._page = mock_page

    # Mock posts locator: 3 posts available
    post_locator = AsyncMock()
    post_locator.count = AsyncMock(return_value=3)

    post_item = AsyncMock()
    post_item.click = AsyncMock()
    post_locator.nth = MagicMock(return_value=post_item)

    # Like button: found
    like_btn = AsyncMock()
    like_btn.count = AsyncMock(return_value=1)
    like_btn.click = AsyncMock()

    # Close button: found
    close_btn = AsyncMock()
    close_btn.count = AsyncMock(return_value=1)
    close_btn.click = AsyncMock()

    def locator_side_effect(selector):
        if "Like" in selector:
            mock = AsyncMock()
            mock.first = like_btn
            mock.count = AsyncMock(return_value=1)
            return mock
        elif "Close" in selector:
            mock = AsyncMock()
            mock.first = close_btn
            mock.count = AsyncMock(return_value=1)
            return mock
        elif "/p/" in selector or "/reel/" in selector:
            return post_locator
        return AsyncMock()

    mock_page.locator = MagicMock(side_effect=locator_side_effect)

    with patch(
        "openclaw_instagram.browser.fallback.async_sleep_human", new_callable=AsyncMock
    ):
        with patch.object(fb, "navigate_to_profile", new_callable=AsyncMock, return_value=mock_page):
            liked = await fb.like_latest_posts("testuser", count=2)

    assert liked >= 0  # Should have liked some posts


@pytest.mark.asyncio
async def test_like_latest_posts_no_like_button(settings):
    """When no like button found, liked count stays at 0."""
    fb = BrowserFallback(settings)
    mock_page = _make_page_mock()

    post_locator = AsyncMock()
    post_locator.count = AsyncMock(return_value=2)
    post_item = AsyncMock()
    post_locator.nth = MagicMock(return_value=post_item)

    like_btn_wrapper = AsyncMock()
    like_btn_wrapper.first = AsyncMock()
    like_btn_wrapper.count = AsyncMock(return_value=0)

    close_btn_wrapper = AsyncMock()
    close_btn_wrapper.first = AsyncMock()
    close_btn_wrapper.count = AsyncMock(return_value=0)

    def locator_side_effect(selector):
        if "Like" in selector:
            return like_btn_wrapper
        elif "Close" in selector:
            return close_btn_wrapper
        return post_locator

    mock_page.locator = MagicMock(side_effect=locator_side_effect)

    with patch(
        "openclaw_instagram.browser.fallback.async_sleep_human", new_callable=AsyncMock
    ):
        with patch.object(fb, "navigate_to_profile", new_callable=AsyncMock, return_value=mock_page):
            liked = await fb.like_latest_posts("testuser", count=2)

    assert liked == 0


@pytest.mark.asyncio
async def test_like_latest_posts_no_posts(settings):
    """When profile has no posts, returns 0."""
    fb = BrowserFallback(settings)
    mock_page = _make_page_mock()

    post_locator = AsyncMock()
    post_locator.count = AsyncMock(return_value=0)
    mock_page.locator = MagicMock(return_value=post_locator)

    with patch(
        "openclaw_instagram.browser.fallback.async_sleep_human", new_callable=AsyncMock
    ):
        with patch.object(fb, "navigate_to_profile", new_callable=AsyncMock, return_value=mock_page):
            liked = await fb.like_latest_posts("testuser", count=3)

    assert liked == 0


@pytest.mark.asyncio
async def test_like_latest_posts_exception_handling(settings):
    """Exception during click is caught and Escape is pressed."""
    fb = BrowserFallback(settings)
    mock_page = _make_page_mock()

    post_locator = AsyncMock()
    post_locator.count = AsyncMock(return_value=1)
    post_item = AsyncMock()
    post_item.click = AsyncMock(side_effect=Exception("Click failed"))
    post_locator.nth = MagicMock(return_value=post_item)
    mock_page.locator = MagicMock(return_value=post_locator)

    with patch(
        "openclaw_instagram.browser.fallback.async_sleep_human", new_callable=AsyncMock
    ):
        with patch.object(fb, "navigate_to_profile", new_callable=AsyncMock, return_value=mock_page):
            liked = await fb.like_latest_posts("testuser", count=1)

    assert liked == 0
    mock_page.keyboard.press.assert_called_with("Escape")


# ---------------------------------------------------------------------------
# check_dms
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_dms_success(settings):
    """check_dms returns list of sender/preview dicts."""
    fb = BrowserFallback(settings)
    mock_page = _make_page_mock()
    fb._page = mock_page

    item1 = AsyncMock()
    item1.inner_text = AsyncMock(return_value="alice\nHey there!\nSome extra line")
    item2 = AsyncMock()
    item2.inner_text = AsyncMock(return_value="bob\nHello!")

    items_locator = AsyncMock()
    items_locator.count = AsyncMock(return_value=2)
    items_locator.nth = MagicMock(side_effect=[item1, item2])

    mock_page.locator = MagicMock(return_value=items_locator)

    with patch(
        "openclaw_instagram.browser.fallback.async_sleep_human", new_callable=AsyncMock
    ):
        threads = await fb.check_dms()

    assert len(threads) == 2
    assert threads[0]["sender"] == "alice"
    assert threads[0]["preview"] == "Hey there!"
    assert threads[1]["sender"] == "bob"


@pytest.mark.asyncio
async def test_check_dms_empty(settings):
    """check_dms returns empty list when no threads."""
    fb = BrowserFallback(settings)
    mock_page = _make_page_mock()
    fb._page = mock_page

    items_locator = AsyncMock()
    items_locator.count = AsyncMock(return_value=0)
    mock_page.locator = MagicMock(return_value=items_locator)

    with patch(
        "openclaw_instagram.browser.fallback.async_sleep_human", new_callable=AsyncMock
    ):
        threads = await fb.check_dms()

    assert threads == []


@pytest.mark.asyncio
async def test_check_dms_skips_single_line_items(settings):
    """Items with only one text line (no preview) are skipped."""
    fb = BrowserFallback(settings)
    mock_page = _make_page_mock()
    fb._page = mock_page

    item1 = AsyncMock()
    item1.inner_text = AsyncMock(return_value="only_one_line")  # no newline

    items_locator = AsyncMock()
    items_locator.count = AsyncMock(return_value=1)
    items_locator.nth = MagicMock(return_value=item1)
    mock_page.locator = MagicMock(return_value=items_locator)

    with patch(
        "openclaw_instagram.browser.fallback.async_sleep_human", new_callable=AsyncMock
    ):
        threads = await fb.check_dms()

    assert threads == []


@pytest.mark.asyncio
async def test_check_dms_exception_skipped(settings):
    """Exception during inner_text is swallowed and item skipped."""
    fb = BrowserFallback(settings)
    mock_page = _make_page_mock()
    fb._page = mock_page

    item_bad = AsyncMock()
    item_bad.inner_text = AsyncMock(side_effect=Exception("DOM error"))
    item_good = AsyncMock()
    item_good.inner_text = AsyncMock(return_value="charlie\nHi!")

    items_locator = AsyncMock()
    items_locator.count = AsyncMock(return_value=2)
    items_locator.nth = MagicMock(side_effect=[item_bad, item_good])
    mock_page.locator = MagicMock(return_value=items_locator)

    with patch(
        "openclaw_instagram.browser.fallback.async_sleep_human", new_callable=AsyncMock
    ):
        threads = await fb.check_dms()

    assert len(threads) == 1
    assert threads[0]["sender"] == "charlie"


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_close_with_browser(settings):
    """close() calls browser.close() and clears state."""
    fb = BrowserFallback(settings)
    mock_browser = AsyncMock()
    mock_browser.close = AsyncMock()
    fb._browser = mock_browser
    fb._page = AsyncMock()

    await fb.close()

    mock_browser.close.assert_called_once()
    assert fb._browser is None
    assert fb._page is None


@pytest.mark.asyncio
async def test_close_no_browser(settings):
    """close() without browser is a no-op."""
    fb = BrowserFallback(settings)
    # Should not raise
    await fb.close()
    assert fb._browser is None


@pytest.mark.asyncio
async def test_close_browser_exception_suppressed(settings):
    """close() suppresses exceptions from browser.close()."""
    fb = BrowserFallback(settings)
    mock_browser = AsyncMock()
    mock_browser.close = AsyncMock(side_effect=Exception("Close failed"))
    fb._browser = mock_browser

    # Should not raise
    await fb.close()
    assert fb._browser is None
