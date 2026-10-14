from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from careslot.shared.db import Base, UTCDateTime


class ConsentDecisionRow(Base):
    """One row per decision; never updated. Current state = latest row per purpose."""

    __tablename__ = "con_decisions"
    __table_args__ = (Index("ix_con_decisions_patient_time", "patient_id", "decided_at"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    patient_id: Mapped[UUID]
    purpose: Mapped[str] = mapped_column(String(40))
    granted: Mapped[bool] = mapped_column(Boolean)
    decided_at: Mapped[datetime] = mapped_column(UTCDateTime())
    policy_version: Mapped[str] = mapped_column(String(16))
