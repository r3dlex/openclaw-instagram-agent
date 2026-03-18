"""Tests for human delay utilities and rate limiter."""

import time

from openclaw_instagram.utils.human_delay import RateLimiter, jittered_delay


def test_jittered_delay_within_bounds():
    for _ in range(100):
        d = jittered_delay(1.0, 5.0)
        assert 1.0 <= d <= 5.0


def test_rate_limiter_allows_actions():
    rl = RateLimiter(max_per_hour=3)
    assert rl.can_act
    assert rl.count_this_hour == 0


def test_rate_limiter_blocks_after_max():
    rl = RateLimiter(max_per_hour=2)
    rl.record()
    rl.record()
    assert not rl.can_act
    assert rl.count_this_hour == 2


def test_rate_limiter_prunes_old():
    rl = RateLimiter(max_per_hour=1)
    rl._timestamps = [time.time() - 3700]  # Older than 1 hour
    assert rl.can_act
    assert rl.count_this_hour == 0


def test_seconds_until_available():
    rl = RateLimiter(max_per_hour=1)
    rl.record()
    wait = rl.seconds_until_available()
    assert 3590 < wait <= 3600


def test_seconds_until_available_when_available():
    rl = RateLimiter(max_per_hour=5)
    assert rl.seconds_until_available() == 0.0
