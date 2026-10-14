from collections.abc import Iterator

import pytest

from careslot.shared.ratelimit import RateLimiter


@pytest.fixture(autouse=True)
def _reset_rate_limits() -> Iterator[None]:
    """Rate limiters are process-global; isolate tests from each other."""
    yield
    for limiter in RateLimiter.instances:
        limiter.reset()
