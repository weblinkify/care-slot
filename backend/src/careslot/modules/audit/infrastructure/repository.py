from collections.abc import Iterator
from datetime import UTC, datetime

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from careslot.modules.audit.application.services import AuditQuery
from careslot.modules.audit.domain.model import GENESIS_HASH, AuditEntry, compute_hash
from careslot.modules.audit.infrastructure.models import AuditEntryRow
from careslot.shared.audit import AuditRecord

# Arbitrary constant identifying "the audit chain" for pg_advisory_xact_lock.
_CHAIN_LOCK_KEY = 72_010_001


def _entry(row: AuditEntryRow) -> AuditEntry:
    return AuditEntry(
        id=row.id,
        occurred_at=row.occurred_at,
        actor_id=row.actor_id,
        actor_role=row.actor_role,
        action=row.action,
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        patient_id=row.patient_id,
        reason=row.reason,
        prev_hash=row.prev_hash,
        hash=row.hash,
    )


class SqlAuditRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def append(self, record: AuditRecord, now: datetime) -> AuditEntry:
        # A hash chain needs a single, linear order of appends. The transaction-scoped
        # advisory lock serialises appenders; it is released at commit/rollback. Cost: audit
        # writes are serialised - fine at this scale; ADR-0004 discusses sharding the chain.
        self._session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _CHAIN_LOCK_KEY})
        prev = self._session.scalar(
            select(AuditEntryRow.hash).order_by(AuditEntryRow.id.desc()).limit(1)
        )
        draft = AuditEntry(
            id=None,
            # Normalise to UTC: the hash covers the ISO string, which must survive a DB round trip.
            occurred_at=now.astimezone(UTC),
            actor_id=record.actor.subject if record.actor else None,
            actor_role=record.actor.role.value if record.actor else None,
            action=record.action,
            resource_type=record.resource_type,
            resource_id=record.resource_id,
            patient_id=record.patient_id,
            reason=record.reason.value,
            prev_hash=prev or GENESIS_HASH,
            hash="",
        )
        digest = compute_hash(draft.prev_hash, draft)
        row = AuditEntryRow(
            occurred_at=draft.occurred_at,
            actor_id=draft.actor_id,
            actor_role=draft.actor_role,
            action=draft.action,
            resource_type=draft.resource_type,
            resource_id=draft.resource_id,
            patient_id=draft.patient_id,
            reason=draft.reason,
            prev_hash=draft.prev_hash,
            hash=digest,
        )
        self._session.add(row)
        self._session.flush()
        return _entry(row)

    def search(self, f: AuditQuery) -> list[AuditEntry]:
        query = select(AuditEntryRow).order_by(AuditEntryRow.id.desc()).limit(f.limit)
        if f.patient_id:
            query = query.where(AuditEntryRow.patient_id == f.patient_id)
        if f.actor_id:
            query = query.where(AuditEntryRow.actor_id == f.actor_id)
        if f.before_id:
            query = query.where(AuditEntryRow.id < f.before_id)
        return [_entry(r) for r in self._session.scalars(query)]

    def iterate_all(self, batch_size: int = 1000) -> Iterator[AuditEntry]:
        # Streams in batches: verifying millions of entries must not load them all at once.
        for row in self._session.scalars(
            select(AuditEntryRow).order_by(AuditEntryRow.id).execution_options(yield_per=batch_size)
        ):
            yield _entry(row)

    def count(self) -> int:
        return self._session.scalar(select(func.count()).select_from(AuditEntryRow)) or 0
