from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, Identity, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from careslot.shared.db import Base, UTCDateTime


class AuditEntryRow(Base):
    """Append-only. UPDATE / DELETE / TRUNCATE are rejected by a trigger (see migration)."""

    __tablename__ = "aud_entries"
    __table_args__ = (
        Index("ix_aud_entries_patient_time", "patient_id", "occurred_at"),
        Index("ix_aud_entries_actor_time", "actor_id", "occurred_at"),
    )

    # Monotonic identity gives the chain its order.
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime())
    actor_id: Mapped[UUID | None]
    actor_role: Mapped[str | None] = mapped_column(String(16))
    action: Mapped[str] = mapped_column(String(64))
    resource_type: Mapped[str] = mapped_column(String(32))
    resource_id: Mapped[str] = mapped_column(String(64))
    patient_id: Mapped[UUID | None]
    reason: Mapped[str] = mapped_column(String(32))
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True)
