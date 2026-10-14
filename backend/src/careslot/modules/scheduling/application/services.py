"""Scheduling use cases.

Each public method is one use case: authorise -> load -> apply domain rule -> persist ->
audit -> publish events. Authorisation lives here (not in the router) so it is enforced for
every caller - HTTP today, a message consumer or CLI tomorrow - and is unit-testable.

Appointments are patient data (an appointment with a physiotherapist says something about a
person's health), so every successful read and write is audited.
"""

from datetime import date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from careslot.modules.scheduling.application.ports import EventPublisher, SchedulingRepository
from careslot.modules.scheduling.domain.model import (
    Appointment,
    Clinic,
    Clinician,
    Slot,
    SlotUnavailableError,
)
from careslot.shared.audit import AccessReason, AuditRecord, AuditSink
from careslot.shared.clock import Clock
from careslot.shared.errors import BusinessRuleError, ForbiddenError, NotFoundError
from careslot.shared.principal import Principal, Role

MAX_SLOT_SEARCH_WINDOW = timedelta(days=31)


class AppointmentNotFoundError(NotFoundError):
    title = "Appointment not found"


class SchedulingService:
    def __init__(
        self,
        repo: SchedulingRepository,
        publish: EventPublisher,
        audit: AuditSink,
        clock: Clock,
    ) -> None:
        self._repo = repo
        self._publish = publish
        self._audit = audit
        self._clock = clock

    # --- queries -------------------------------------------------------------------------

    def list_clinics(self) -> list[tuple[Clinic, list[Clinician]]]:
        return self._repo.list_clinics()

    def available_slots(self, clinician_id: UUID, start: datetime, end: datetime) -> list[Slot]:
        if end <= start or end - start > MAX_SLOT_SEARCH_WINDOW:
            # Bounded search window: an unbounded range is an easy accidental DoS.
            raise BusinessRuleError(
                f"Search window must be positive and at most {MAX_SLOT_SEARCH_WINDOW.days} days."
            )
        if self._repo.get_clinician(clinician_id) is None:
            raise NotFoundError("Clinician not found")
        return self._repo.available_slots(clinician_id, max(start, self._clock()), end)

    def my_appointments(self, principal: Principal) -> list[Appointment]:
        self._require(principal, Role.PATIENT)
        appointments = self._repo.list_for_patient(principal.subject)
        self._record(
            principal, "appointment.list", "patient", str(principal.subject), principal.subject
        )
        return appointments

    def get_appointment(self, principal: Principal, appointment_id: UUID) -> Appointment:
        appointment = self._repo.get_appointment(appointment_id)
        if appointment is None or not self._can_view(principal, appointment):
            # Same response whether it does not exist or belongs to someone else (no enumeration).
            raise AppointmentNotFoundError()
        self._record_appointment(principal, "appointment.read", appointment)
        return appointment

    def clinician_day(self, principal: Principal, day: date) -> list[Appointment]:
        """A clinician's appointments for one calendar day in the clinic's own timezone."""
        self._require(principal, Role.CLINICIAN)
        clinician = self._repo.get_clinician(principal.subject)
        if clinician is None:
            raise NotFoundError("Clinician not found")
        clinic = self._repo.get_clinic(clinician.clinic_id)
        tz = ZoneInfo(clinic.timezone if clinic else "UTC")
        start = datetime.combine(day, time.min, tzinfo=tz)
        appointments = self._repo.list_for_clinician(clinician.id, start, start + timedelta(days=1))
        # One entry per patient shown: "who accessed which patient's data" must be answerable
        # per patient, not hidden inside a single "schedule viewed" row.
        for appointment in appointments:
            self._record_appointment(principal, "appointment.read", appointment)
        return appointments

    # --- commands ------------------------------------------------------------------------

    def book(self, principal: Principal, slot_id: UUID) -> Appointment:
        # The patient id comes from the verified token, never from the request body, so a
        # patient cannot book on someone else's behalf.
        self._require(principal, Role.PATIENT)
        slot = self._get_free_slot(slot_id)
        appointment = Appointment.book(patient_id=principal.subject, slot=slot, now=self._clock())
        self._repo.add(appointment)
        self._record_appointment(principal, "appointment.book", appointment)
        self._flush_events(appointment)
        return appointment

    def reschedule(
        self, principal: Principal, appointment_id: UUID, new_slot_id: UUID
    ) -> Appointment:
        appointment = self._get_own_appointment(principal, appointment_id)
        new_slot = self._get_free_slot(new_slot_id)
        appointment.reschedule(new_slot=new_slot, now=self._clock())
        self._repo.save(appointment)
        self._record_appointment(principal, "appointment.reschedule", appointment)
        self._flush_events(appointment)
        return appointment

    def cancel(self, principal: Principal, appointment_id: UUID) -> Appointment:
        appointment = self._get_own_appointment(principal, appointment_id)
        appointment.cancel(now=self._clock())
        self._repo.save(appointment)
        self._record_appointment(principal, "appointment.cancel", appointment)
        self._flush_events(appointment)
        return appointment

    # --- helpers -------------------------------------------------------------------------

    def _get_free_slot(self, slot_id: UUID) -> Slot:
        slot = self._repo.get_slot(slot_id)
        if slot is None:
            raise NotFoundError("Slot not found")
        # Fast, friendly check. The partial unique index in the database is the real guard
        # against two concurrent bookings of the same slot (see repository).
        if self._repo.is_slot_booked(slot_id):
            raise SlotUnavailableError()
        return slot

    def _get_own_appointment(self, principal: Principal, appointment_id: UUID) -> Appointment:
        appointment = self._repo.get_appointment(appointment_id)
        if appointment is None or not principal.is_patient(appointment.patient_id):
            raise AppointmentNotFoundError()
        return appointment

    @staticmethod
    def _can_view(principal: Principal, appointment: Appointment) -> bool:
        if principal.role is Role.PATIENT:
            return principal.subject == appointment.patient_id
        if principal.role is Role.CLINICIAN:
            return principal.subject == appointment.clinician_id
        return False  # Admins audit access; they do not browse clinical appointments.

    @staticmethod
    def _require(principal: Principal, role: Role) -> None:
        if principal.role is not role:
            raise ForbiddenError(f"This action requires the {role} role.")

    def _record_appointment(
        self, principal: Principal, action: str, appointment: Appointment
    ) -> None:
        self._record(principal, action, "appointment", str(appointment.id), appointment.patient_id)

    def _record(
        self,
        principal: Principal,
        action: str,
        resource_type: str,
        resource_id: str,
        patient_id: UUID,
    ) -> None:
        reason = (
            AccessReason.SELF_SERVICE
            if principal.role is Role.PATIENT
            else AccessReason.APPOINTMENT_PREPARATION
        )
        self._audit(
            AuditRecord(
                actor=principal,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                patient_id=patient_id,
                reason=reason,
            )
        )

    def _flush_events(self, appointment: Appointment) -> None:
        for event in appointment.pending_events:
            self._publish(event)
        appointment.pending_events.clear()
