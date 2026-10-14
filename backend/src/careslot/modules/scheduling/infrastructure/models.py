"""Scheduling tables. Every table is prefixed `sched_` and owned by this module only.

`patient_id` deliberately has no foreign key to the patients module's table: modules own
their data and could be split into separate databases later (ADR-0001). Referential
consistency across modules is maintained through domain events (e.g. erasure).
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from careslot.shared.db import Base, UTCDateTime


class ClinicRow(Base):
    __tablename__ = "sched_clinics"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    timezone: Mapped[str] = mapped_column(String(64))


class ClinicianRow(Base):
    __tablename__ = "sched_clinicians"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    clinic_id: Mapped[UUID] = mapped_column(ForeignKey("sched_clinics.id"), index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    specialty: Mapped[str] = mapped_column(String(80))


class SlotRow(Base):
    __tablename__ = "sched_slots"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="positive_duration"),
        Index("ix_sched_slots_clinician_start", "clinician_id", "starts_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    clinician_id: Mapped[UUID] = mapped_column(ForeignKey("sched_clinicians.id"))
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime())
    ends_at: Mapped[datetime] = mapped_column(UTCDateTime())


class AppointmentRow(Base):
    __tablename__ = "sched_appointments"
    __table_args__ = (
        # THE double-booking guard. Partial unique index: at most one *active* appointment
        # per slot. Cancelled rows are kept for history and do not block re-booking. Two
        # concurrent requests that both pass the application check still cannot both commit.
        Index(
            "uq_sched_appointments_active_slot",
            "slot_id",
            unique=True,
            postgresql_where=text("status = 'booked'"),
        ),
        Index("ix_sched_appointments_clinician_start", "clinician_id", "starts_at"),
        CheckConstraint("status IN ('booked', 'cancelled')", name="valid_status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    patient_id: Mapped[UUID] = mapped_column(index=True)
    clinician_id: Mapped[UUID] = mapped_column(ForeignKey("sched_clinicians.id"))
    slot_id: Mapped[UUID] = mapped_column(ForeignKey("sched_slots.id"))
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime())
    ends_at: Mapped[datetime] = mapped_column(UTCDateTime())
    status: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    cancelled_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
