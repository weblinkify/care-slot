"""Request/response contracts for the scheduling API (part of the OpenAPI spec).

Kept separate from domain objects so the public contract can stay stable while the domain
evolves. `extra="forbid"` rejects unknown fields: typos and mass-assignment attempts (e.g.
sending `patient_id`) fail loudly instead of being silently ignored.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from careslot.modules.scheduling.domain.model import (
    Appointment,
    AppointmentStatus,
    Clinic,
    Clinician,
    Slot,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClinicianOut(BaseModel):
    id: UUID
    display_name: str
    specialty: str

    @classmethod
    def of(cls, c: Clinician) -> "ClinicianOut":
        return cls(id=c.id, display_name=c.display_name, specialty=c.specialty)


class ClinicOut(BaseModel):
    id: UUID
    name: str
    timezone: str = Field(examples=["Europe/Helsinki"])
    clinicians: list[ClinicianOut]

    @classmethod
    def of(cls, clinic: Clinic, clinicians: list[Clinician]) -> "ClinicOut":
        return cls(
            id=clinic.id,
            name=clinic.name,
            timezone=clinic.timezone,
            clinicians=[ClinicianOut.of(c) for c in clinicians],
        )


class SlotOut(BaseModel):
    id: UUID
    clinician_id: UUID
    starts_at: datetime
    ends_at: datetime

    @classmethod
    def of(cls, s: Slot) -> "SlotOut":
        return cls(id=s.id, clinician_id=s.clinician_id, starts_at=s.starts_at, ends_at=s.ends_at)


class BookAppointmentIn(StrictModel):
    slot_id: UUID


class RescheduleAppointmentIn(StrictModel):
    slot_id: UUID = Field(description="The new slot to move the appointment to.")


class AppointmentOut(BaseModel):
    id: UUID
    clinician_id: UUID
    slot_id: UUID
    starts_at: datetime
    ends_at: datetime
    status: AppointmentStatus
    created_at: datetime
    cancelled_at: datetime | None

    @classmethod
    def of(cls, a: Appointment) -> "AppointmentOut":
        return cls(
            id=a.id,
            clinician_id=a.clinician_id,
            slot_id=a.slot_id,
            starts_at=a.starts_at,
            ends_at=a.ends_at,
            status=a.status,
            created_at=a.created_at,
            cancelled_at=a.cancelled_at,
        )
