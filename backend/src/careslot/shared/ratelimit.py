"""Fixed-window rate limiter for brute-force-sensitive endpoints (login).

Deliberately simple and in-process. Limitation, stated honestly: with several API replicas
each one counts separately, so the effective limit is N x replicas. Production would enforce
this at the API gateway / WAF or in a shared store (Redis). The interface would not change.
"""

import threading
import time
from collections.abc import Callable
from typing import ClassVar

from careslot.shared.errors import DomainError


class RateLimitedError(DomainError):
    status = 429
    code = "rate-limited"
    title = "Too many requests"

    def __init__(self, retry_after: int) -> None:
        super().__init__(f"Try again in {retry_after} seconds.")
        self.retry_after = retry_after


class RateLimiter:
    instances: ClassVar[list["RateLimiter"]] = []

    def __init__(
        self, limit: int, window_seconds: int, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.limit = limit
        self.window = window_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._hits: dict[str, tuple[float, int]] = {}
        RateLimiter.instances.append(self)

    def hit(self, key: str) -> None:
        now = self._clock()
        with self._lock:
            started, count = self._hits.get(key, (now, 0))
            if now - started >= self.window:
                started, count = now, 0
            count += 1
            self._hits[key] = (started, count)
            if count > self.limit:
                raise RateLimitedError(retry_after=max(1, int(self.window - (now - started))))

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
