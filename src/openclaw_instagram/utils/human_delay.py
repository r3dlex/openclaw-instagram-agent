"""Human-like delay utilities to avoid detection and rate limiting."""

from __future__ import annotations

import asyncio
import random
import time

import structlog

logger = structlog.get_logger()


def jittered_delay(min_seconds: float, max_seconds: float) -> float:
    """Generate a human-like delay with gaussian jitter around the midpoint."""
    midpoint = (min_seconds + max_seconds) / 2
    std_dev = (max_seconds - min_seconds) / 4
    delay = max(min_seconds, min(max_seconds, random.gauss(midpoint, std_dev)))
    return round(delay, 2)


def sleep_human(min_seconds: float = 2.0, max_seconds: float = 8.0) -> float:
    """Synchronous human-like sleep. Returns actual delay used."""
    delay = jittered_delay(min_seconds, max_seconds)
    logger.debug("human_delay", seconds=delay)
    time.sleep(delay)
    return delay


async def async_sleep_human(min_seconds: float = 2.0, max_seconds: float = 8.0) -> float:
    """Async human-like sleep. Returns actual delay used."""
    delay = jittered_delay(min_seconds, max_seconds)
    logger.debug("human_delay_async", seconds=delay)
    await asyncio.sleep(delay)
    return delay


class RateLimiter:
    """Track actions per hour and enforce limits."""

    def __init__(self, max_per_hour: int = 20) -> None:
        self.max_per_hour = max_per_hour
        self._timestamps: list[float] = []

    def _prune(self) -> None:
        cutoff = time.time() - 3600
        self._timestamps = [t for t in self._timestamps if t > cutoff]

    @property
    def count_this_hour(self) -> int:
        self._prune()
        return len(self._timestamps)

    @property
    def can_act(self) -> bool:
        return self.count_this_hour < self.max_per_hour

    def record(self) -> None:
        self._timestamps.append(time.time())

    def seconds_until_available(self) -> float:
        if self.can_act:
            return 0.0
        self._prune()
        if not self._timestamps:
            return 0.0
        oldest = self._timestamps[0]
        return max(0.0, oldest + 3600 - time.time())
