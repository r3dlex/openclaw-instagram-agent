"""Telegram notification client for important agent events.

Sends messages to a configured Telegram chat via the Bot API.
Silently no-ops if credentials are not configured.
"""

from __future__ import annotations

import httpx
import structlog

logger = structlog.get_logger()

_SEND_MESSAGE_URL = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramNotifier:
    """Send notifications to Telegram. No-ops gracefully when unconfigured."""

    def __init__(self, bot_token: str = "", chat_id: str = "") -> None:
        self._token = bot_token
        self._chat_id = chat_id
        self._enabled = bool(bot_token and chat_id)
        if not self._enabled:
            logger.debug("telegram_disabled", reason="missing bot_token or chat_id")

    @property
    def enabled(self) -> bool:
        return self._enabled

    def send(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send a message synchronously. Returns True on success."""
        if not self._enabled:
            return False

        url = _SEND_MESSAGE_URL.format(token=self._token)
        payload = {
            "chat_id": self._chat_id,
            "text": message,
            "parse_mode": parse_mode,
        }

        try:
            resp = httpx.post(url, json=payload, timeout=10.0)
            if resp.status_code == 200:
                logger.info("telegram_sent", length=len(message))
                return True
            logger.warning(
                "telegram_send_failed",
                status=resp.status_code,
                body=resp.text[:200],
            )
            return False
        except Exception as e:
            logger.error("telegram_error", error=str(e))
            return False

    def notify_engagement_done(
        self, results: dict[str, dict], method: str = "mixed"
    ) -> bool:
        """Send an engagement summary."""
        total_liked = sum(r.get("liked", 0) for r in results.values())
        errors = [
            f"  {u}: {', '.join(r['errors'])}"
            for u, r in results.items()
            if r.get("errors")
        ]

        lines = [
            "<b>Engagement cycle complete</b>",
            f"Accounts: {len(results)}",
            f"Liked: {total_liked}",
        ]
        if errors:
            lines.append("\n<b>Errors:</b>\n" + "\n".join(errors))

        return self.send("\n".join(lines))

    def notify_api_cooldown(self, hours: int) -> bool:
        """Notify that API entered cooldown."""
        return self.send(
            f"<b>API cooldown activated</b>\n"
            f"Falling back to browser.\n"
            f"Retry in {hours}h."
        )

    def notify_dms(self, dms: list[dict]) -> bool:
        """Notify about new DMs requiring attention."""
        if not dms:
            return False
        lines = ["<b>DMs requiring attention</b>"]
        for dm in dms[:10]:
            user = dm.get("username", "unknown")
            preview = dm.get("preview", "")[:80]
            lines.append(f"  <b>{user}:</b> {preview}")
        return self.send("\n".join(lines))

    def notify_error(self, context: str, error: str) -> bool:
        """Notify about a critical error."""
        return self.send(
            f"<b>Error: {context}</b>\n<code>{error[:500]}</code>"
        )
