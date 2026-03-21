"""Inter-Agent Message Queue (IAMQ) client.

Connects to the openclaw-inter-agent-message-queue service for
agent-to-agent communication, discovery, and coordination.
"""

from __future__ import annotations

import threading
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


class IAMQClient:
    """HTTP client for the Inter-Agent Message Queue service."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:18790",
        agent_id: str = "instagram_agent",
        enabled: bool = False,
        heartbeat_interval: int = 240,
        poll_interval: int = 30,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._agent_id = agent_id
        self._enabled = enabled
        self._heartbeat_interval = heartbeat_interval
        self._poll_interval = poll_interval
        self._metadata = metadata or {}
        self._heartbeat_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def agent_id(self) -> str:
        return self._agent_id

    # ---- Core API Methods ----

    def register(self) -> bool:
        """Register this agent with the message queue (incl. metadata). Returns True on success."""
        if not self._enabled:
            return False
        try:
            payload: dict[str, Any] = {"agent_id": self._agent_id, **self._metadata}
            resp = httpx.post(
                f"{self._base_url}/register",
                json=payload,
                timeout=10,
            )
            if resp.status_code == 200:
                logger.info("iamq_registered", agent_id=self._agent_id)
                return True
            logger.warning(
                "iamq_register_failed",
                status=resp.status_code,
                body=resp.text[:200],
            )
            return False
        except Exception as e:
            logger.error("iamq_register_error", error=str(e))
            return False

    def heartbeat(self) -> bool:
        """Send heartbeat to keep registration alive. Returns True on success."""
        if not self._enabled:
            return False
        try:
            resp = httpx.post(
                f"{self._base_url}/heartbeat",
                json={"agent_id": self._agent_id},
                timeout=10,
            )
            if resp.status_code == 200:
                logger.debug("iamq_heartbeat_sent", agent_id=self._agent_id)
                return True
            logger.warning("iamq_heartbeat_failed", status=resp.status_code)
            return False
        except Exception as e:
            logger.error("iamq_heartbeat_error", error=str(e))
            return False

    def send(
        self,
        to: str,
        subject: str,
        body: str,
        *,
        msg_type: str = "info",
        priority: str = "NORMAL",
        reply_to: str | None = None,
        expires_at: str | None = None,
    ) -> dict[str, Any] | None:
        """Send a message to another agent or 'broadcast'. Returns message dict or None."""
        if not self._enabled:
            return None
        payload: dict[str, Any] = {
            "from": self._agent_id,
            "to": to,
            "type": msg_type,
            "priority": priority,
            "subject": subject,
            "body": body,
        }
        if reply_to:
            payload["replyTo"] = reply_to
        if expires_at:
            payload["expiresAt"] = expires_at
        try:
            resp = httpx.post(
                f"{self._base_url}/send",
                json=payload,
                timeout=10,
            )
            if resp.status_code == 201:
                msg = resp.json()
                logger.info(
                    "iamq_message_sent",
                    to=to,
                    subject=subject,
                    msg_id=msg.get("id"),
                )
                return msg
            logger.warning("iamq_send_failed", status=resp.status_code, body=resp.text[:200])
            return None
        except Exception as e:
            logger.error("iamq_send_error", error=str(e))
            return None

    def inbox(self, status: str | None = "unread") -> list[dict[str, Any]]:
        """Fetch messages from this agent's inbox. Defaults to unread only."""
        if not self._enabled:
            return []
        try:
            params = {"status": status} if status else {}
            resp = httpx.get(
                f"{self._base_url}/inbox/{self._agent_id}",
                params=params,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                messages = data.get("messages", [])
                if messages:
                    logger.info("iamq_inbox_polled", count=len(messages))
                return messages
            logger.warning("iamq_inbox_failed", status=resp.status_code)
            return []
        except Exception as e:
            logger.error("iamq_inbox_error", error=str(e))
            return []

    def update_status(self, message_id: str, status: str) -> bool:
        """Update a message's status (read, acted, archived). Returns True on success."""
        if not self._enabled:
            return False
        try:
            resp = httpx.patch(
                f"{self._base_url}/messages/{message_id}",
                json={"status": status},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error("iamq_status_update_error", error=str(e), message_id=message_id)
            return False

    def get_agents(self) -> list[dict[str, Any]]:
        """List all registered agents. Returns list of agent dicts."""
        if not self._enabled:
            return []
        try:
            resp = httpx.get(f"{self._base_url}/agents", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                # Handle both {"agents": [...]} and bare [...] formats
                return data.get("agents", data) if isinstance(data, dict) else data
            return []
        except Exception as e:
            logger.error("iamq_agents_error", error=str(e))
            return []

    def get_status(self) -> dict[str, Any] | None:
        """Get queue health/status summary."""
        if not self._enabled:
            return None
        try:
            resp = httpx.get(f"{self._base_url}/status", timeout=10)
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception as e:
            logger.error("iamq_status_error", error=str(e))
            return None

    # ---- Lifecycle ----

    def start(self) -> None:
        """Register and start background heartbeat thread."""
        if not self._enabled:
            logger.info("iamq_disabled")
            return
        self.register()
        self._stop_event.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, daemon=True, name="iamq-heartbeat"
        )
        self._heartbeat_thread.start()
        logger.info(
            "iamq_started",
            agent_id=self._agent_id,
            heartbeat_interval=self._heartbeat_interval,
        )

    def stop(self) -> None:
        """Stop background heartbeat thread."""
        self._stop_event.set()
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=5)
        logger.info("iamq_stopped", agent_id=self._agent_id)

    def _heartbeat_loop(self) -> None:
        """Background loop: send heartbeat at configured interval."""
        while not self._stop_event.is_set():
            self.heartbeat()
            self._stop_event.wait(timeout=self._heartbeat_interval)

    # ---- Convenience ----

    def broadcast(self, subject: str, body: str, **kwargs: Any) -> dict[str, Any] | None:
        """Broadcast a message to all agents."""
        return self.send("broadcast", subject, body, **kwargs)

    def announce_engagement(self, results: dict[str, Any]) -> dict[str, Any] | None:
        """Announce engagement cycle results to all agents."""
        total_liked = sum(r.get("liked", 0) for r in results.values())
        total_errors = sum(len(r.get("errors", [])) for r in results.values())
        accounts = list(results.keys())
        body = (
            f"Engagement cycle complete.\n"
            f"Accounts: {', '.join(accounts)}\n"
            f"Total liked: {total_liked}\n"
            f"Errors: {total_errors}"
        )
        return self.broadcast(
            subject=f"Engagement done: {total_liked} likes across {len(accounts)} accounts",
            body=body,
        )

    def announce_error(self, context: str, error: str) -> dict[str, Any] | None:
        """Announce a critical error to all agents."""
        return self.broadcast(
            subject=f"Error: {context}",
            body=f"Context: {context}\nError: {error}",
            priority="HIGH",
            msg_type="error",
        )

    def announce_api_cooldown(self, hours: int) -> dict[str, Any] | None:
        """Announce API cooldown to all agents."""
        return self.broadcast(
            subject=f"Instagram API entering {hours}h cooldown",
            body=f"API rate-limited or challenged. Falling back to browser for {hours} hours.",
            priority="HIGH",
            msg_type="info",
        )
