"""Scheduling domain events. Part of the module's public interface (re-exported in
`careslot.modules.scheduling`). Events carry IDs only, never personal data."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from careslot.shared.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class AppointmentBooked(DomainEvent):
    appointment_id: UUID
    patient_id: UUID
    clinician_id: UUID
    starts_at: datetime


@dataclass(frozen=True, kw_only=True)
class AppointmentRescheduled(DomainEvent):
    appointment_id: UUID
    patient_id: UUID
    previous_slot_id: UUID
    new_slot_id: UUID
    starts_at: datetime


@dataclass(frozen=True, kw_only=True)
class AppointmentCancelled(DomainEvent):
    appointment_id: UUID
    patient_id: UUID
    # A closed enum value, so safe to put on an event (events never carry free text).
    reason: str | None = None
