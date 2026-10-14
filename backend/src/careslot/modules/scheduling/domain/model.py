"""Scheduling domain: clinics, clinicians, bookable slots and appointments.

Pure Python - no framework or database imports - so the business rules can be read, reviewed
and unit-tested in isolation. Persistence and HTTP are adapters around this core.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4

from careslot.modules.scheduling.domain.events import (
    AppointmentBooked,
    AppointmentCancelled,
    AppointmentRescheduled,
)
from careslot.shared.errors import BusinessRuleError, ConflictError
from careslot.shared.events import DomainEvent

# Patients may not change an appointment shortly before it starts: the clinic cannot refill
# the slot that late. A real system would make this a per-clinic policy.
CHANGE_CUTOFF = timedelta(hours=2)


class AppointmentStatus(StrEnum):
    BOOKED = "booked"
    CANCELLED = "cancelled"


class SlotInPastError(BusinessRuleError):
    code = "slot-in-past"
    title = "Slot has already started"


class ChangeWindowClosedError(BusinessRuleError):
    code = "change-window-closed"
    title = "Appointment can no longer be changed"


class AppointmentNotActiveError(ConflictError):
    code = "appointment-not-active"
    title = "Appointment is not active"


class SlotUnavailableError(ConflictError):
    code = "slot-unavailable"
    title = "Slot is no longer available"


@dataclass(frozen=True)
class Clinic:
    id: UUID
    name: str
    timezone: str


@dataclass(frozen=True)
class Clinician:
    id: UUID
    clinic_id: UUID
    display_name: str
    specialty: str


@dataclass(frozen=True)
class Slot:
    id: UUID
    clinician_id: UUID
    starts_at: datetime
    ends_at: datetime


@dataclass
class Appointment:
    """Aggregate root. All state changes go through methods that enforce the rules and
    record a domain event; nothing outside this class assigns `status` directly."""

    id: UUID
    patient_id: UUID
    clinician_id: UUID
    slot_id: UUID
    starts_at: datetime
    ends_at: datetime
    status: AppointmentStatus
    created_at: datetime
    cancelled_at: datetime | None = None
    pending_events: list[DomainEvent] = field(default_factory=list, repr=False, compare=False)

    @classmethod
    def book(cls, *, patient_id: UUID, slot: Slot, now: datetime) -> "Appointment":
        if slot.starts_at <= now:
            raise SlotInPastError()
        appointment = cls(
            id=uuid4(),
            patient_id=patient_id,
            clinician_id=slot.clinician_id,
            slot_id=slot.id,
            starts_at=slot.starts_at,
            ends_at=slot.ends_at,
            status=AppointmentStatus.BOOKED,
            created_at=now,
        )
        appointment.pending_events.append(
            AppointmentBooked(
                appointment_id=appointment.id,
                patient_id=patient_id,
                clinician_id=slot.clinician_id,
                starts_at=slot.starts_at,
            )
        )
        return appointment

    def reschedule(self, *, new_slot: Slot, now: datetime) -> None:
        self._ensure_changeable(now)
        if new_slot.starts_at <= now:
            raise SlotInPastError()
        previous_slot_id = self.slot_id
        self.slot_id = new_slot.id
        self.clinician_id = new_slot.clinician_id
        self.starts_at = new_slot.starts_at
        self.ends_at = new_slot.ends_at
        self.pending_events.append(
            AppointmentRescheduled(
                appointment_id=self.id,
                patient_id=self.patient_id,
                previous_slot_id=previous_slot_id,
                new_slot_id=new_slot.id,
                starts_at=new_slot.starts_at,
            )
        )

    def cancel(self, *, now: datetime) -> None:
        self._ensure_changeable(now)
        self.status = AppointmentStatus.CANCELLED
        self.cancelled_at = now
        self.pending_events.append(
            AppointmentCancelled(appointment_id=self.id, patient_id=self.patient_id)
        )

    def cancel_by_system(self, *, now: datetime) -> None:
        """Cancellation the patient did not request (e.g. erasure). The change cut-off protects
        the clinic from late patient changes; it does not apply when the patient no longer
        exists in the system and will not attend."""
        if self.status is not AppointmentStatus.BOOKED:
            raise AppointmentNotActiveError()
        self.status = AppointmentStatus.CANCELLED
        self.cancelled_at = now
        self.pending_events.append(
            AppointmentCancelled(appointment_id=self.id, patient_id=self.patient_id)
        )

    def _ensure_changeable(self, now: datetime) -> None:
        if self.status is not AppointmentStatus.BOOKED:
            raise AppointmentNotActiveError()
        if now > self.starts_at - CHANGE_CUTOFF:
            raise ChangeWindowClosedError(
                f"Changes are not possible later than {CHANGE_CUTOFF} before the start time."
            )
