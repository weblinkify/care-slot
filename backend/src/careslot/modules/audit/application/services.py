"""Audit use cases: append (for every module, via the AuditSink port) and admin review."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from careslot.modules.audit.domain.model import AuditEntry, ChainVerification, verify_chain
from careslot.shared.audit import AccessReason, AuditRecord
from careslot.shared.clock import Clock
from careslot.shared.errors import ForbiddenError
from careslot.shared.principal import Principal, Role

MAX_PAGE = 200


@dataclass(frozen=True)
class AuditQuery:
    patient_id: UUID | None = None
    actor_id: UUID | None = None
    before_id: int | None = None  # keyset pagination: stable while new entries arrive
    limit: int = 50


class AuditRepository(Protocol):
    def append(self, record: AuditRecord, now: datetime) -> AuditEntry: ...
    def search(self, query: AuditQuery) -> list[AuditEntry]: ...
    def iterate_all(self) -> Iterator[AuditEntry]: ...


class AuditService:
    def __init__(self, repo: AuditRepository, clock: Clock) -> None:
        self._repo = repo
        self._clock = clock

    def record(self, record: AuditRecord) -> None:
        self._repo.append(record, self._clock())

    def search(self, principal: Principal, query: AuditQuery) -> list[AuditEntry]:
        self._require_admin(principal)
        # Reading the audit log is itself audited: who watches the watchers.
        self.record(
            AuditRecord(
                actor=principal,
                action="audit.search",
                resource_type="audit_log",
                resource_id=str(query.patient_id or query.actor_id or "*"),
                patient_id=query.patient_id,
                reason=AccessReason.AUDIT_REVIEW,
            )
        )
        return self._repo.search(query)

    def verify(self, principal: Principal) -> ChainVerification:
        self._require_admin(principal)
        return verify_chain(self._repo.iterate_all())

    @staticmethod
    def _require_admin(principal: Principal) -> None:
        if principal.role is not Role.ADMIN:
            raise ForbiddenError("Only administrators can review the audit log.")
