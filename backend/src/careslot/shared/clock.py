"""Injectable clock. Business rules depend on "now"; tests pass a fixed time instead of
patching `datetime`, which keeps time-based rules (cut-offs, retention) deterministic."""

from collections.abc import Callable
from datetime import UTC, datetime

Clock = Callable[[], datetime]


def system_clock() -> datetime:
    return datetime.now(UTC)
