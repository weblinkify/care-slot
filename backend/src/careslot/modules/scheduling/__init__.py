"""Scheduling bounded context: clinics, clinicians, slots and appointments.

PUBLIC INTERFACE. Other modules may import only what is re-exported here (enforced by
import-linter). Everything under domain/, application/, infrastructure/ and api/ is private.
"""

from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from careslot.modules.scheduling.domain.events import (
    AppointmentBooked,
    AppointmentCancelled,
    AppointmentRescheduled,
)
from careslot.modules.scheduling.infrastructure.repository import has_care_relationship


def care_relationship_checker(session: Session) -> Callable[[UUID, UUID], bool]:
    """(clinician_id, patient_id) -> does a care relationship exist? Used by `patients`."""
    return lambda clinician_id, patient_id: has_care_relationship(session, clinician_id, patient_id)


__all__ = [
    "AppointmentBooked",
    "AppointmentCancelled",
    "AppointmentRescheduled",
    "care_relationship_checker",
]
