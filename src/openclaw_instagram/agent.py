"""Main agent orchestrator: coordinates API client and browser fallback."""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from openclaw_instagram.api.client import InstagramAPIClient
from openclaw_instagram.browser.fallback import BrowserFallback
from openclaw_instagram.config import Settings, get_settings
from openclaw_instagram.utils.human_delay import sleep_human
from openclaw_instagram.utils.logging import setup_logging

logger = structlog.get_logger()


class InstagramAgent:
    """Orchestrates Instagram engagement across API and browser backends.

    Strategy:
    1. Try API client first (fast, lower detection risk with proper delays).
    2. If API is in cooldown (rate limited / challenge), fall back to browser.
    3. After api_retry_hours, attempt API again.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        setup_logging(self.settings.log_level, self.settings.log_dir)
        self.api = InstagramAPIClient(self.settings)
        self.browser = BrowserFallback(self.settings)

    def engage_accounts(self, usernames: list[str]) -> dict[str, Any]:
        """Run engagement cycle on a list of accounts. Returns summary."""
        results: dict[str, Any] = {}

        for username in usernames:
            logger.info("engaging_account", username=username)

            if self.api.api_available:
                result = self._engage_via_api(username)
            else:
                result = asyncio.run(self._engage_via_browser(username))

            results[username] = result
            sleep_human(
                self.settings.min_action_delay_seconds,
                self.settings.max_action_delay_seconds,
            )

        return results

    def _engage_via_api(self, username: str) -> dict[str, Any]:
        """Engage with a single account via API."""
        result: dict[str, Any] = {"method": "api", "liked": 0, "errors": []}

        user_id = self.api.get_user_id(username)
        if not user_id:
            result["errors"].append(f"Could not resolve user: {username}")
            return result

        medias = self.api.get_user_medias(user_id, count=5)
        for media in medias:
            if self.api.like_media(media.id):
                result["liked"] += 1

        logger.info("api_engagement_done", username=username, liked=result["liked"])
        return result

    async def _engage_via_browser(self, username: str) -> dict[str, Any]:
        """Engage with a single account via browser fallback."""
        result: dict[str, Any] = {"method": "browser", "liked": 0, "errors": []}

        try:
            liked = await self.browser.like_latest_posts(username, count=3)
            result["liked"] = liked
        except Exception as e:
            result["errors"].append(str(e))
            logger.error("browser_engagement_error", username=username, error=str(e))

        logger.info("browser_engagement_done", username=username, liked=result["liked"])
        return result

    def check_dms(self, filter_usernames: list[str] | None = None) -> list[dict[str, Any]]:
        """Check DMs, optionally filtering by sender usernames."""
        if self.api.api_available:
            threads = self.api.get_direct_threads()
            messages = []
            for thread in threads:
                for user in getattr(thread, "users", []):
                    uname = getattr(user, "username", "")
                    if filter_usernames and uname not in filter_usernames:
                        continue
                    messages.append({
                        "thread_id": getattr(thread, "id", ""),
                        "username": uname,
                        "source": "api",
                    })
            return messages
        else:
            return asyncio.run(self._check_dms_browser(filter_usernames))

    async def _check_dms_browser(
        self, filter_usernames: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Check DMs via browser fallback."""
        threads = await self.browser.check_dms()
        if filter_usernames:
            threads = [t for t in threads if t.get("sender") in filter_usernames]
        return [
            {"username": t["sender"], "preview": t["preview"], "source": "browser"}
            for t in threads
        ]

    def close(self) -> None:
        """Clean up all resources."""
        self.api.close()
        asyncio.run(self.browser.close())
