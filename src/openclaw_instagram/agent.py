"""Main agent orchestrator: coordinates API client and browser fallback."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import structlog

from openclaw_instagram.api.client import InstagramAPIClient
from openclaw_instagram.browser.fallback import BrowserFallback
from openclaw_instagram.config import Settings, get_settings
from openclaw_instagram.utils.human_delay import sleep_human
from openclaw_instagram.utils.iamq import IAMQClient
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
        self.iamq = IAMQClient(
            base_url=self.settings.iamq_http_url,
            agent_id=self.settings.iamq_agent_id,
            enabled=self.settings.iamq_enabled,
            heartbeat_interval=self.settings.iamq_heartbeat_interval,
            poll_interval=self.settings.iamq_poll_interval,
            metadata={
                "name": "InstaOps \U0001f4f8",
                "emoji": "\U0001f4f8",
                "description": (
                    "Autonomous Instagram engagement agent "
                    "\u2014 likes posts/reels, monitors DMs, reports via IAMQ"
                ),
                "capabilities": [
                    "instagram_engage",
                    "instagram_dms",
                    "instagram_like",
                    "instagram_status",
                ],
                "workspace": str(Path.cwd()),
            },
        )
        self.api = InstagramAPIClient(
            self.settings, iamq_client=self.iamq
        )
        self.browser = BrowserFallback(self.settings)
        self.iamq.start()

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

        self.iamq.announce_engagement(results)
        return results

    def _engage_via_api(self, username: str) -> dict[str, Any]:
        """Engage with a single account via API: like all new posts, comment on new reels."""
        result: dict[str, Any] = {
            "method": "api", "liked": 0, "commented": 0, "skipped": 0,
            "posts": [], "errors": [],
        }

        user_id = self.api.get_user_id(username)
        if not user_id:
            result["errors"].append(f"Could not resolve user: {username}")
            return result

        liked_cache = self.api.get_liked_posts()
        commented_cache = self.api.get_commented_posts()
        medias = self.api.get_user_medias(user_id, count=10)

        for media in medias:
            pk = str(media.pk)
            media_type = {1: "Photo", 2: "Video/Reel", 8: "Album"}.get(media.media_type, "Post")
            caption = getattr(media, "caption_text", "") or ""

            # Skip if already liked
            if pk in liked_cache:
                result["skipped"] += 1
                continue

            # Always like new posts
            if self.api.like_media(media.id):
                self.api.mark_liked(pk)
                result["liked"] += 1

            # Comment on new reels (not already commented)
            comment_text = None
            if media_type == "Video/Reel" and pk not in commented_cache:
                comment_text = self._generate_comment(username, caption, media_type)
                if comment_text:
                    try:
                        self.api.media_comment(pk, comment_text)
                        self.api.mark_commented(pk)
                        result["commented"] += 1
                    except Exception as e:
                        logger.warning("comment_failed", pk=pk, error=str(e))

            summary = f"{media_type}: {caption[:100]}" if caption else media_type
            result["posts"].append({
                "pk": pk, "type": media_type, "summary": summary,
                "commented": bool(comment_text),
            })

        logger.info(
            "api_engagement_done",
            username=username, liked=result["liked"],
            commented=result["commented"], skipped=result["skipped"],
        )
        return result

    def _generate_comment(self, username: str, caption: str, media_type: str) -> str | None:
        """Generate a contextual comment in the language of the post."""
        caption_lower = caption.lower()

        # stuttgart_blog — German
        if username == "stuttgart_blog":
            if any(w in caption_lower for w in ["stuttgart", "west", "stadt", "platz", "restaurant", "cafe", "bar", "food", "essen"]):
                return "Toller Tipp! Stuttgart West hat so viel zu bieten 👏"
            if any(w in caption_lower for w in ["magnolien", "wilhelma", "blumen", "park", "garten", "natur"]):
                return "Die Magnolien in der Wilhelma sind unglaublich schön! Danke für den Tipp 🌸"
            if any(w in caption_lower for w in ["stuttgart 21", "bau", "baustelle", "tunnel", "zug", "bahn"]):
                return "Faszinierend! So ein exklusiver Blick hinter die Kulissen von Stuttgart 21 🚧"
            if any(w in caption_lower for w in ["business", "linkedin", "foto", "portrait", "porträt"]):
                return "Du siehst großartig auf den neuen Fotos! So mutig, sich vor die Linse zu trauen 📸"
            if any(w in caption_lower for w in ["terrasse", "sonne", "sonnenterrasse", "aussicht", "genieß"]):
                return "Diese Terrasse muss ich dieses Jahr unbedingt besuchen! 😎☀️"
            if any(w in caption_lower for w in ["indoor", "spielplatz", "kinder", "spaß"]):
                return "Toller Spot! Spielen und Genießen mitten in Stuttgart 🎉"
            if any(w in caption_lower for w in ["artbeat", "malen", "kreativ", "aktion", "painting"]):
                return "So eine coole Idee! Kreativ sein in Stuttgart 👀✨"
            if any(w in caption_lower for w in [" Mauritius", "beach", "urlaub", "urlaubsgefühl"]):
                return "Das Mauritius Beach kenne ich noch gar nicht! Urlaubsfeeling mitten in der Stadt, wow! ☀️🏖️"
            if any(w in caption_lower for w in ["perlen", "schmuck", "studio", "gestalten"]):
                return "So eine tolle Idee! Schmuck selber machen in Stuttgart 👀✨"
            if any(w in caption_lower for w in ["pizza", "pasta", "restaurant", "italienisch", "food"]):
                return "Pizza oder Pasta? Warum entscheiden... wenn man beides haben kann? 🍕🍝"
            if any(w in caption_lower for w in ["workshop", "frauenpower", "konzept", " empowerment"]):
                return "Starke Frauenpower in Stuttgart! 🚀💪"
            if any(w in caption_lower for w in ["abnehmen", "fitness", "gesund", "wellness"]):
                return "Siehst super aus! Motivation pur 💪✨"
            if any(w in caption_lower for w in ["gewinnspiel", "schenken", "geschenk", "free"]):
                return "Danke für das Gewinnspiel! 🏆😊"
            return "Super Beitrag! 👏"

        # stuttgartmitkind — German
        elif username == "stuttgartmitkind":
            if any(w in caption_lower for w in ["artbeat", "malen", "kreativ", "gemalt"]):
                return "Artbeat.stg sieht mega aus! Nicky war ja direkt kreativ 🎨🤩"
            if any(w in caption_lower for w in ["mauritius", "my_mauritius", "spiel", "spaß"]):
                return "Mauri Games klingt nach perfektem Spaß für Nicky! 😄🎮"
            if any(w in caption_lower for w in ["indoor", "spielplatz", "innenstadt"]):
                return "Ein neuer Indoor-Spielplatz in der Innenstadt? Nicky war wohl sofort Fan! 👀🎢"
            if any(w in caption_lower for w in ["buildabearde", "laden", "kuscheltier", "teddy"]):
                return "Build-a-Beard klingt nach einem Abenteuer! Nickys Kuscheltier ist so cute ✂️🐻"
            if any(w in caption_lower for w in ["spielzeug", "testen", "monat"]):
                return "Monatliches Spielzeug zum Testen? Nicky hat bestimmt Spaß dabei! 🎁🧸"
            if any(w in caption_lower for w in [" crêpes", "workshop", "kochen", "backen"]):
                return "Nicky hat ja selbst Crêpes gemacht! 🥞 So cool!"
            if any(w in caption_lower for w in ["weihnachtsmarkt", "weihnachten", "weihnacht", "glühwein"]):
                return "Der Weihnachtsmarkt-Zauber bleibt immer! Staunende Augen 👀🎄"
            if any(w in caption_lower for w in ["kinder", "perspektive", "nicky", "entdeckt"]):
                return "Nicky als Reporter 🧒📣 Die Perspektive von Kindern ist so wertvoll!"
            if any(w in caption_lower for w in [" Indoor", "hüpfburg", "boxauto", "ritts"]):
                return "Das klingt nach dem perfekten Tag für Nicky! Spielen und Essen 🍽️🚗"
            if any(w in caption_lower for w in ["werbung", "sponsored", "anzeige"]):
                return "Sieht nach perfektem Spaß für die ganze Familie aus! 😊"
            return "Nicky hat sichtlich Spaß! 🧒✨"

        # ankes_insta — mixed DE/EN
        elif username == "ankes_insta":
            if any(w in caption_lower for w in ["love", "liebe", "relationship", "paar", "couple"]):
                return "Wunderschöne Liebesgeschichte! ❤️ So schön, dass ihr sie bei @ichhier_dudort teilt!"
            if any(w in caption_lower for w in ["floriano", "baby", "newborn", "bruder"]):
                return "One year with Floriano already! 🥳 Wishing you all the love in the world! 💕"
            if any(w in caption_lower for w in ["greece", "griechenland", "sommer", "sonne", "urlaub"]):
                return "Greece looks absolutely beautiful! 🇬🇷☀️ Love the vibes!"
            if any(w in caption_lower for w in ["turkey", "türkei", "extended summer"]):
                return "Extended summer in Turkey sounds like paradise! 🇹🇷☀️🌸"
            if any(w in caption_lower for w in ["colorfully", "languages", "greeting", "introduce"]):
                return "What a wonderful contribution to OursColorfully Languages! Greetings from Stuttgart 🇩🇪✨"
            if any(w in caption_lower for w in ["podcast", "where are they now", "archival"]):
                return "Love this 'where are they now' update! 📻✨ Always so heartwarming!"
            if any(w in caption_lower for w in ["floriano"]):
                return "Welcome to the world, Floriano! 💕 Wishing your family all the love!"
            return "Beautiful content! 💕"

        return None

    async def _engage_via_browser(self, username: str) -> dict[str, Any]:
        """Engage with a single account via browser fallback."""
        result: dict[str, Any] = {"method": "browser", "liked": 0, "errors": []}

        try:
            liked = await self.browser.like_latest_posts(username, count=3)
            result["liked"] = liked
        except Exception as e:
            result["errors"].append(str(e))
            logger.error("browser_engagement_error", username=username, error=str(e))
            self.iamq.announce_error("browser_engagement", str(e))

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
        else:
            messages = asyncio.run(self._check_dms_browser(filter_usernames))

        return messages

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

    def poll_iamq(self) -> list[dict[str, Any]]:
        """Poll IAMQ inbox for messages from other agents."""
        return self.iamq.inbox(status="unread")

    def get_peer_agents(self) -> list[dict[str, Any]]:
        """Discover other agents registered with the message queue."""
        return self.iamq.get_agents()

    def close(self) -> None:
        """Clean up all resources."""
        self.iamq.stop()
        self.api.close()
        asyncio.run(self.browser.close())
