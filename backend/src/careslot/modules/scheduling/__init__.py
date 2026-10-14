"""Scheduling bounded context: clinics, clinicians, slots and appointments.

PUBLIC INTERFACE. Other modules may import only what is re-exported here (enforced by
import-linter). Everything under domain/, application/, infrastructure/ and api/ is private.
"""

from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from careslot.modules.audit import make_audit_sink
from careslot.modules.patients import PatientErased
from careslot.modules.scheduling.application.services import SchedulingService
from careslot.modules.scheduling.domain.events import (
    AppointmentBooked,
    AppointmentCancelled,
    AppointmentRescheduled,
)
from careslot.modules.scheduling.infrastructure.repository import (
    SqlSchedulingRepository,
    has_care_relationship,
)
from careslot.shared.clock import system_clock
from careslot.shared.events import event_bus


def care_relationship_checker(session: Session) -> Callable[[UUID, UUID], bool]:
    """(clinician_id, patient_id) -> does a care relationship exist? Used by `patients`."""
    return lambda clinician_id, patient_id: has_care_relationship(session, clinician_id, patient_id)


def system_service(session: Session) -> SchedulingService:
    """Service instance for event handlers and jobs (no HTTP request, no principal)."""
    return SchedulingService(
        repo=SqlSchedulingRepository(session),
        publish=lambda event: event_bus.publish(event, session),
        audit=make_audit_sink(session),
        clock=system_clock,
    )


def on_patient_erased(event: PatientErased, session: Session) -> None:
    """An erased patient will not attend: free their future slots for others."""
    system_service(session).cancel_future_for_erased_patient(event.patient_id)


__all__ = [
    "AppointmentBooked",
    "AppointmentCancelled",
    "AppointmentRescheduled",
    "care_relationship_checker",
    "on_patient_erased",
    "system_service",
]
