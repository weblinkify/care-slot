"""In-process domain event bus.

Why in-process (ADR-0002): one deployable, one database, one transaction. Handlers run
synchronously inside the publisher's transaction, so "appointment booked" and every side
effect of it commit or roll back together - no lost or phantom events, no broker to operate.

Why it can move to a broker later without touching modules:
- events are immutable, flat, JSON-serialisable dataclasses (`to_message()`),
- publishers only know `EventBus.publish`, subscribers only know the event type,
- no handler returns a value to the publisher.
The migration path is a transactional outbox: `publish` writes the message to an outbox
table in the same transaction and a relay forwards it to the broker.
"""

import dataclasses
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Protocol, TypeVar
from uuid import UUID, uuid4

from sqlalchemy.orm import Session


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def name(self) -> str:
        return type(self).__name__

    def to_message(self) -> dict[str, Any]:
        """Broker-ready representation (IDs only - events never carry personal data)."""

        def encode(value: Any) -> Any:
            if isinstance(value, UUID):
                return str(value)
            if isinstance(value, datetime):
                return value.isoformat()
            if isinstance(value, Enum):
                return value.value
            return value

        return {"name": self.name} | {k: encode(v) for k, v in dataclasses.asdict(self).items()}


E = TypeVar("E", bound=DomainEvent)
E_contra = TypeVar("E_contra", bound=DomainEvent, contravariant=True)


class EventHandler(Protocol[E_contra]):
    def __call__(self, event: E_contra, session: Session) -> None: ...


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[Callable[[Any, Session], None]]] = defaultdict(
            list
        )

    def subscribe(self, event_type: type[E], handler: EventHandler[E]) -> None:
        # Idempotent: the composition root may run more than once per process (tests, jobs).
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    def publish(self, event: DomainEvent, session: Session) -> None:
        for handler in self._handlers[type(event)]:
            handler(event, session)


# One bus per process; wired in the composition root (careslot.main).
event_bus = EventBus()
