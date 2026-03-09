"""Rate limiting with jitter and backoff."""

from __future__ import annotations

import random
import time

from clix.core.constants import DEFAULT_DELAY_SECONDS, WRITE_DELAY_RANGE


def delay(base: float = DEFAULT_DELAY_SECONDS, jitter_factor: float = 0.5) -> None:
    """Sleep with randomized jitter.

    Actual delay = base * uniform(1 - jitter_factor, 1 + jitter_factor)
    """
    actual = base * random.uniform(1 - jitter_factor, 1 + jitter_factor)
    time.sleep(max(0.1, actual))


def write_delay() -> None:
    """Sleep for a random duration appropriate for write operations."""
    time.sleep(random.uniform(*WRITE_DELAY_RANGE))


def backoff_delay(attempt: int, base: float = 2.0, max_delay: float = 60.0) -> None:
    """Exponential backoff with jitter."""
    wait = min(base * (2**attempt) + random.uniform(0, 1), max_delay)
    time.sleep(wait)
