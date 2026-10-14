"""In-memory test doubles for the scheduling ports. Synthetic data only."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from careslot.modules.scheduling.domain.model import (
    Appointment,
    AppointmentStatus,
    Clinic,
    Clinician,
    Slot,
)
from careslot.shared.events import DomainEvent

NOW = datetime(2026, 3, 2, 8, 0, tzinfo=UTC)  # a Monday


class FakeSchedulingRepository:
    def __init__(self) -> None:
        self.clinic = Clinic(id=uuid4(), name="Synthetic Health Centre", timezone="Europe/Helsinki")
        self.clinician = Clinician(
            id=uuid4(), clinic_id=self.clinic.id, display_name="Dr. Test", specialty="General"
        )
        self.slots: dict[UUID, Slot] = {}
        self.appointments: dict[UUID, Appointment] = {}

    def make_slot(self, starts_in: timedelta) -> Slot:
        start = NOW + starts_in
        slot = Slot(
            id=uuid4(),
            clinician_id=self.clinician.id,
            starts_at=start,
            ends_at=start + timedelta(minutes=30),
        )
        self.slots[slot.id] = slot
        return slot

    # --- port implementation ---
    def list_clinics(self) -> list[tuple[Clinic, list[Clinician]]]:
        return [(self.clinic, [self.clinician])]

    def get_clinic(self, clinic_id: UUID) -> Clinic | None:
        return self.clinic if clinic_id == self.clinic.id else None

    def get_clinician(self, clinician_id: UUID) -> Clinician | None:
        return self.clinician if clinician_id == self.clinician.id else None

    def get_slot(self, slot_id: UUID) -> Slot | None:
        return self.slots.get(slot_id)

    def available_slots(self, clinician_id: UUID, start: datetime, end: datetime) -> list[Slot]:
        return sorted(
            (
                s
                for s in self.slots.values()
                if s.clinician_id == clinician_id
                and start <= s.starts_at < end
                and not self.is_slot_booked(s.id)
            ),
            key=lambda s: s.starts_at,
        )

    def is_slot_booked(self, slot_id: UUID) -> bool:
        return any(
            a.slot_id == slot_id and a.status is AppointmentStatus.BOOKED
            for a in self.appointments.values()
        )

    def get_appointment(self, appointment_id: UUID) -> Appointment | None:
        found = self.appointments.get(appointment_id)
        return replace(found, pending_events=[]) if found else None  # copy, like a real load

    def list_for_patient(self, patient_id: UUID) -> list[Appointment]:
        return [a for a in self.appointments.values() if a.patient_id == patient_id]

    def list_for_clinician(
        self, clinician_id: UUID, start: datetime, end: datetime
    ) -> list[Appointment]:
        return [
            a
            for a in self.appointments.values()
            if a.clinician_id == clinician_id
            and a.status is AppointmentStatus.BOOKED
            and start <= a.starts_at < end
        ]

    def add(self, appointment: Appointment) -> None:
        self.appointments[appointment.id] = appointment

    def save(self, appointment: Appointment) -> None:
        self.appointments[appointment.id] = appointment


class RecordingPublisher:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    def __call__(self, event: DomainEvent) -> None:
        self.events.append(event)

    @property
    def names(self) -> list[str]:
        return [e.name for e in self.events]
