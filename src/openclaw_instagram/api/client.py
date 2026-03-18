"""Instagram API client using instagrapi with human-like behavior.

Uses instagrapi (maintained private API wrapper) as primary method.
Falls back to browser automation if API is blocked/stalled.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import structlog
from instagrapi import Client as InstaClient
from instagrapi.exceptions import (
    ChallengeRequired,
    LoginRequired,
    PleaseWaitFewMinutes,
    RateLimitError,
)

from openclaw_instagram.config import Settings
from openclaw_instagram.utils.human_delay import RateLimiter, sleep_human

logger = structlog.get_logger()

SESSION_CACHE_DIR = Path("session_cache")
SESSION_FILE = SESSION_CACHE_DIR / "session.json"
API_FAILURE_FILE = SESSION_CACHE_DIR / "api_failure_timestamp"


class InstagramAPIClient:
    """Instagram API client with session persistence and human-like delays."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.rate_limiter = RateLimiter(max_per_hour=settings.max_actions_per_hour)
        self._client: InstaClient | None = None
        self._api_available = True

    @property
    def api_available(self) -> bool:
        """Check if API is available (not in cooldown from prior failure)."""
        if not self._api_available and API_FAILURE_FILE.exists():
            failure_time = float(API_FAILURE_FILE.read_text().strip())
            hours_elapsed = (time.time() - failure_time) / 3600
            if hours_elapsed < self.settings.api_retry_hours:
                logger.info(
                    "api_in_cooldown",
                    hours_remaining=round(self.settings.api_retry_hours - hours_elapsed, 1),
                )
                return False
            # Cooldown expired, retry
            API_FAILURE_FILE.unlink(missing_ok=True)
            self._api_available = True
        return self._api_available

    def _mark_api_failed(self) -> None:
        """Record API failure timestamp for cooldown tracking."""
        SESSION_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        API_FAILURE_FILE.write_text(str(time.time()))
        self._api_available = False
        logger.warning(
            "api_marked_failed",
            retry_after_hours=self.settings.api_retry_hours,
        )

    def _get_client(self) -> InstaClient:
        """Get or create authenticated instagrapi client with session reuse."""
        if self._client is not None:
            return self._client

        client = InstaClient()

        # Human-like device settings
        client.delay_range = [
            self.settings.min_action_delay_seconds,
            self.settings.max_action_delay_seconds,
        ]

        # Try to restore saved session
        SESSION_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        if SESSION_FILE.exists():
            try:
                session_data = json.loads(SESSION_FILE.read_text())
                client.set_settings(session_data)
                client.login(self.settings.instagram_username, self.settings.instagram_password)
                logger.info("session_restored")
                self._client = client
                return client
            except Exception:
                logger.warning("session_restore_failed_relogin")
                SESSION_FILE.unlink(missing_ok=True)

        # Fresh login
        client.login(self.settings.instagram_username, self.settings.instagram_password)
        SESSION_FILE.write_text(json.dumps(client.get_settings()))
        logger.info("fresh_login_success")
        self._client = client
        return client

    def _save_session(self) -> None:
        """Persist current session to disk."""
        if self._client:
            SESSION_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            SESSION_FILE.write_text(json.dumps(self._client.get_settings()))

    def _safe_call(self, fn_name: str, *args: Any, **kwargs: Any) -> Any:
        """Execute an API call with rate limiting, delays, and error handling."""
        if not self.rate_limiter.can_act:
            wait = self.rate_limiter.seconds_until_available()
            logger.warning("rate_limit_self_imposed", wait_seconds=round(wait))
            return None

        sleep_human(
            self.settings.min_action_delay_seconds,
            self.settings.max_action_delay_seconds,
        )

        client = self._get_client()
        fn = getattr(client, fn_name)

        try:
            result = fn(*args, **kwargs)
            self.rate_limiter.record()
            self._save_session()
            logger.info("api_call_success", method=fn_name)
            return result
        except (RateLimitError, PleaseWaitFewMinutes) as e:
            logger.error("instagram_rate_limit", method=fn_name, error=str(e))
            self._mark_api_failed()
            return None
        except ChallengeRequired as e:
            logger.error("instagram_challenge_required", method=fn_name, error=str(e))
            self._mark_api_failed()
            return None
        except LoginRequired:
            logger.warning("session_expired_relogin", method=fn_name)
            self._client = None
            SESSION_FILE.unlink(missing_ok=True)
            try:
                self._get_client()
                return self._safe_call(fn_name, *args, **kwargs)
            except Exception as e2:
                logger.error("relogin_failed", error=str(e2))
                self._mark_api_failed()
                return None
        except Exception as e:
            logger.error("api_call_error", method=fn_name, error=str(e))
            return None

    # ---- Public engagement methods ----

    def get_user_id(self, username: str) -> int | None:
        """Resolve username to user PK."""
        result = self._safe_call("user_id_from_username", username)
        return int(result) if result else None

    def get_user_medias(self, user_id: int, count: int = 5) -> list[Any]:
        """Get recent media for a user."""
        result = self._safe_call("user_medias", user_id, count)
        return result or []

    def like_media(self, media_id: str) -> bool:
        """Like a single media item."""
        result = self._safe_call("media_like", media_id)
        return bool(result)

    def get_direct_threads(self) -> list[Any]:
        """Get recent DM threads."""
        result = self._safe_call("direct_threads")
        return result or []

    def get_direct_messages(self, thread_id: int, count: int = 20) -> list[Any]:
        """Get messages from a specific DM thread."""
        result = self._safe_call("direct_messages", thread_id, count)
        return result or []

    def get_user_stories(self, user_id: int) -> list[Any]:
        """Get current stories for a user."""
        result = self._safe_call("user_stories", user_id)
        return result or []

    def close(self) -> None:
        """Save session and clean up."""
        self._save_session()
        self._client = None
