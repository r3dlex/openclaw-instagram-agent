"""Browser-based Instagram fallback using Playwright.

Activated when the API client is in cooldown (rate limited or challenge required).
Connects to an existing browser via CDP or launches a new one.
"""

from __future__ import annotations

import contextlib

import structlog
from playwright.async_api import Browser, Page, async_playwright

from openclaw_instagram.config import Settings
from openclaw_instagram.utils.human_delay import async_sleep_human

logger = structlog.get_logger()


class BrowserFallback:
    """Playwright-based browser automation for Instagram when API is unavailable."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._browser: Browser | None = None
        self._page: Page | None = None

    async def _get_page(self) -> Page:
        """Connect to existing browser via CDP or launch new one."""
        if self._page and not self._page.is_closed():
            return self._page

        pw = await async_playwright().start()

        cdp_url = f"http://{self.settings.browser_cdp_host}:{self.settings.browser_cdp_port}"
        try:
            self._browser = await pw.chromium.connect_over_cdp(cdp_url)
            contexts = self._browser.contexts
            if contexts and contexts[0].pages:
                self._page = contexts[0].pages[0]
            else:
                context = contexts[0] if contexts else await self._browser.new_context()
                self._page = await context.new_page()
            logger.info("browser_cdp_connected", url=cdp_url)
        except Exception as e:
            logger.warning("cdp_connect_failed", error=str(e))
            self._browser = await pw.chromium.launch(headless=True)
            context = await self._browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 430, "height": 932},
                is_mobile=True,
            )
            self._page = await context.new_page()
            logger.info("browser_launched_headless")

        return self._page

    async def navigate_to_profile(self, username: str) -> Page:
        """Navigate to an Instagram user profile."""
        page = await self._get_page()
        await page.goto(f"https://www.instagram.com/{username}/", wait_until="networkidle")
        await async_sleep_human(2.0, 5.0)
        return page

    async def like_latest_posts(self, username: str, count: int = 3) -> int:
        """Like the latest N posts from a user profile via browser. Returns count liked."""
        page = await self.navigate_to_profile(username)
        liked = 0

        # Click on posts grid
        posts = page.locator("article a[href*='/p/'], article a[href*='/reel/']")
        post_count = await posts.count()

        for i in range(min(count, post_count)):
            try:
                await posts.nth(i).click()
                await async_sleep_human(1.5, 3.0)

                # Find and click the like button (heart icon that isn't already liked)
                like_btn = page.locator(
                    'svg[aria-label="Like"][width="24"]'
                ).first
                if await like_btn.count() > 0:
                    await like_btn.click()
                    liked += 1
                    logger.info("browser_liked_post", username=username, index=i)
                    await async_sleep_human(1.0, 2.5)

                # Close the post modal
                close_btn = page.locator('svg[aria-label="Close"]').first
                if await close_btn.count() > 0:
                    await close_btn.click()
                    await async_sleep_human(0.5, 1.5)

            except Exception as e:
                logger.warning("browser_like_error", username=username, index=i, error=str(e))
                # Try pressing Escape to close any modal
                await page.keyboard.press("Escape")
                await async_sleep_human(1.0, 2.0)

        return liked

    async def check_dms(self) -> list[dict[str, str]]:
        """Check DM inbox via browser. Returns list of {sender, preview}."""
        page = await self._get_page()
        await page.goto("https://www.instagram.com/direct/inbox/", wait_until="networkidle")
        await async_sleep_human(2.0, 4.0)

        threads: list[dict[str, str]] = []
        items = page.locator('[role="listbox"] > div > div')
        count = min(10, await items.count())

        for i in range(count):
            try:
                item = items.nth(i)
                text = await item.inner_text()
                lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
                if len(lines) >= 2:
                    threads.append({"sender": lines[0], "preview": lines[1]})
            except Exception:
                continue

        return threads

    async def close(self) -> None:
        """Clean up browser resources."""
        if self._browser:
            with contextlib.suppress(Exception):
                await self._browser.close()
            self._browser = None
            self._page = None
