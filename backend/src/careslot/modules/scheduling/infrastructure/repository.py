"""SQLAlchemy implementation of `SchedulingRepository`.

Maps between ORM rows and domain objects explicitly. More code than using ORM classes as
the domain model, but the domain stays free of persistence concerns and the mapping is the
single place that knows both shapes.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from careslot.modules.scheduling.domain.model import (
    Appointment,
    AppointmentStatus,
    Clinic,
    Clinician,
    Slot,
    SlotUnavailableError,
)
from careslot.modules.scheduling.infrastructure.models import (
    AppointmentRow,
    ClinicianRow,
    ClinicRow,
    SlotRow,
)


def _clinic(row: ClinicRow) -> Clinic:
    return Clinic(id=row.id, name=row.name, timezone=row.timezone)


def _clinician(row: ClinicianRow) -> Clinician:
    return Clinician(
        id=row.id, clinic_id=row.clinic_id, display_name=row.display_name, specialty=row.specialty
    )


def _slot(row: SlotRow) -> Slot:
    return Slot(
        id=row.id, clinician_id=row.clinician_id, starts_at=row.starts_at, ends_at=row.ends_at
    )


def _appointment(row: AppointmentRow) -> Appointment:
    return Appointment(
        id=row.id,
        patient_id=row.patient_id,
        clinician_id=row.clinician_id,
        slot_id=row.slot_id,
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        status=AppointmentStatus(row.status),
        created_at=row.created_at,
        cancelled_at=row.cancelled_at,
    )


_ACTIVE = AppointmentStatus.BOOKED.value


class SqlSchedulingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_clinics(self) -> list[tuple[Clinic, list[Clinician]]]:
        clinics = self._session.scalars(select(ClinicRow).order_by(ClinicRow.name)).all()
        clinicians = self._session.scalars(
            select(ClinicianRow).order_by(ClinicianRow.display_name)
        ).all()
        return [
            (_clinic(c), [_clinician(x) for x in clinicians if x.clinic_id == c.id])
            for c in clinics
        ]

    def get_clinic(self, clinic_id: UUID) -> Clinic | None:
        row = self._session.get(ClinicRow, clinic_id)
        return _clinic(row) if row else None

    def get_clinician(self, clinician_id: UUID) -> Clinician | None:
        row = self._session.get(ClinicianRow, clinician_id)
        return _clinician(row) if row else None

    def get_slot(self, slot_id: UUID) -> Slot | None:
        row = self._session.get(SlotRow, slot_id)
        return _slot(row) if row else None

    def available_slots(self, clinician_id: UUID, start: datetime, end: datetime) -> list[Slot]:
        booked = exists().where(
            AppointmentRow.slot_id == SlotRow.id, AppointmentRow.status == _ACTIVE
        )
        rows = self._session.scalars(
            select(SlotRow)
            .where(
                SlotRow.clinician_id == clinician_id,
                SlotRow.starts_at >= start,
                SlotRow.starts_at < end,
                ~booked,
            )
            .order_by(SlotRow.starts_at)
        ).all()
        return [_slot(r) for r in rows]

    def is_slot_booked(self, slot_id: UUID) -> bool:
        return bool(
            self._session.scalar(
                select(
                    exists().where(
                        AppointmentRow.slot_id == slot_id, AppointmentRow.status == _ACTIVE
                    )
                )
            )
        )

    def get_appointment(self, appointment_id: UUID) -> Appointment | None:
        row = self._session.get(AppointmentRow, appointment_id)
        return _appointment(row) if row else None

    def list_for_patient(self, patient_id: UUID) -> list[Appointment]:
        rows = self._session.scalars(
            select(AppointmentRow)
            .where(AppointmentRow.patient_id == patient_id)
            .order_by(AppointmentRow.starts_at)
        ).all()
        return [_appointment(r) for r in rows]

    def list_for_clinician(
        self, clinician_id: UUID, start: datetime, end: datetime
    ) -> list[Appointment]:
        rows = self._session.scalars(
            select(AppointmentRow)
            .where(
                AppointmentRow.clinician_id == clinician_id,
                AppointmentRow.status == _ACTIVE,
                AppointmentRow.starts_at >= start,
                AppointmentRow.starts_at < end,
            )
            .order_by(AppointmentRow.starts_at)
        ).all()
        return [_appointment(r) for r in rows]

    def list_future_for_patient(self, patient_id: UUID, now: datetime) -> list[Appointment]:
        rows = self._session.scalars(
            select(AppointmentRow).where(
                AppointmentRow.patient_id == patient_id, AppointmentRow.starts_at > now
            )
        ).all()
        return [_appointment(r) for r in rows]

    def purge_ended_before(self, cutoff: datetime) -> tuple[int, int]:
        appointments = self._session.execute(
            delete(AppointmentRow).where(AppointmentRow.ends_at < cutoff)
        )
        has_appointment = exists().where(AppointmentRow.slot_id == SlotRow.id)
        slots = self._session.execute(
            delete(SlotRow).where(SlotRow.ends_at < cutoff, ~has_appointment)
        )
        return int(appointments.rowcount), int(slots.rowcount)  # type: ignore[attr-defined]

    def add(self, appointment: Appointment) -> None:
        self._session.add(
            AppointmentRow(
                id=appointment.id,
                patient_id=appointment.patient_id,
                clinician_id=appointment.clinician_id,
                slot_id=appointment.slot_id,
                starts_at=appointment.starts_at,
                ends_at=appointment.ends_at,
                status=appointment.status.value,
                created_at=appointment.created_at,
                cancelled_at=appointment.cancelled_at,
            )
        )
        self._flush()

    def save(self, appointment: Appointment) -> None:
        row = self._session.get_one(AppointmentRow, appointment.id)
        row.clinician_id = appointment.clinician_id
        row.slot_id = appointment.slot_id
        row.starts_at = appointment.starts_at
        row.ends_at = appointment.ends_at
        row.status = appointment.status.value
        row.cancelled_at = appointment.cancelled_at
        self._flush()

    def _flush(self) -> None:
        # Flush now (not at commit) so a lost booking race surfaces as a clean 409 from
        # inside the use case, rather than as a 500 when the request transaction commits.
        try:
            self._session.flush()
        except IntegrityError as exc:
            if "uq_sched_appointments_active_slot" in str(exc.orig):
                raise SlotUnavailableError() from exc
            raise


def has_care_relationship(session: Session, clinician_id: UUID, patient_id: UUID) -> bool:
    """True if the clinician has (or had) any appointment with the patient."""
    return bool(
        session.scalar(
            select(
                exists().where(
                    AppointmentRow.clinician_id == clinician_id,
                    AppointmentRow.patient_id == patient_id,
                )
            )
        )
    )
