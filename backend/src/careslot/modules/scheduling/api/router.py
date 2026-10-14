"""Scheduling HTTP endpoints. Thin by design: parse, call one use case, map the result.

State changes are explicit commands (`POST .../cancel`) rather than `DELETE`: a cancelled
appointment is kept for history and audit, and the verb documents intent in the access log.
"""

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from careslot.modules.scheduling.api.schemas import (
    AppointmentOut,
    BookAppointmentIn,
    ClinicOut,
    RescheduleAppointmentIn,
    SlotOut,
)
from careslot.modules.scheduling.application.services import SchedulingService
from careslot.modules.scheduling.infrastructure.repository import SqlSchedulingRepository
from careslot.shared.clock import system_clock
from careslot.shared.db import get_session
from careslot.shared.errors import PROBLEM_RESPONSES
from careslot.shared.events import event_bus
from careslot.shared.principal import Role
from careslot.shared.security import CurrentPrincipal, get_principal, require_role


def get_scheduling_service(session: Annotated[Session, Depends(get_session)]) -> SchedulingService:
    return SchedulingService(
        repo=SqlSchedulingRepository(session),
        publish=lambda event: event_bus.publish(event, session),
        clock=system_clock,
    )


Service = Annotated[SchedulingService, Depends(get_scheduling_service)]

router = APIRouter(
    tags=["scheduling"],
    dependencies=[Depends(get_principal)],  # every scheduling endpoint requires a valid token
    responses={k: PROBLEM_RESPONSES[k] for k in (401, 403, 404, 422)},
)


@router.get("/clinics", response_model=list[ClinicOut], summary="List clinics and clinicians")
def list_clinics(service: Service) -> list[ClinicOut]:
    return [ClinicOut.of(clinic, clinicians) for clinic, clinicians in service.list_clinics()]


@router.get(
    "/clinicians/{clinician_id}/slots",
    response_model=list[SlotOut],
    summary="Free slots for a clinician in a time window (max 31 days)",
)
def available_slots(
    clinician_id: UUID,
    service: Service,
    from_: Annotated[
        datetime, Query(alias="from", description="Window start (ISO 8601, with offset)")
    ],
    to: Annotated[datetime, Query(description="Window end (exclusive)")],
) -> list[SlotOut]:
    return [SlotOut.of(s) for s in service.available_slots(clinician_id, from_, to)]


@router.post(
    "/appointments",
    response_model=AppointmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Book a slot for the calling patient",
    responses={409: PROBLEM_RESPONSES[409]},
    dependencies=[require_role(Role.PATIENT)],
)
def book(body: BookAppointmentIn, principal: CurrentPrincipal, service: Service) -> AppointmentOut:
    return AppointmentOut.of(service.book(principal, body.slot_id))


@router.get(
    "/appointments",
    response_model=list[AppointmentOut],
    summary="The calling patient's appointments",
    dependencies=[require_role(Role.PATIENT)],
)
def my_appointments(principal: CurrentPrincipal, service: Service) -> list[AppointmentOut]:
    return [AppointmentOut.of(a) for a in service.my_appointments(principal)]


@router.get("/appointments/{appointment_id}", response_model=AppointmentOut)
def get_appointment(
    appointment_id: UUID, principal: CurrentPrincipal, service: Service
) -> AppointmentOut:
    return AppointmentOut.of(service.get_appointment(principal, appointment_id))


@router.post(
    "/appointments/{appointment_id}/reschedule",
    response_model=AppointmentOut,
    responses={409: PROBLEM_RESPONSES[409]},
    dependencies=[require_role(Role.PATIENT)],
)
def reschedule(
    appointment_id: UUID,
    body: RescheduleAppointmentIn,
    principal: CurrentPrincipal,
    service: Service,
) -> AppointmentOut:
    return AppointmentOut.of(service.reschedule(principal, appointment_id, body.slot_id))


@router.post(
    "/appointments/{appointment_id}/cancel",
    response_model=AppointmentOut,
    responses={409: PROBLEM_RESPONSES[409]},
    dependencies=[require_role(Role.PATIENT)],
)
def cancel(appointment_id: UUID, principal: CurrentPrincipal, service: Service) -> AppointmentOut:
    return AppointmentOut.of(service.cancel(principal, appointment_id))


@router.get(
    "/clinicians/me/schedule",
    response_model=list[AppointmentOut],
    summary="The calling clinician's appointments for one day (clinic timezone)",
    dependencies=[require_role(Role.CLINICIAN)],
)
def my_schedule(
    principal: CurrentPrincipal, service: Service, day: Annotated[date, Query()]
) -> list[AppointmentOut]:
    return [AppointmentOut.of(a) for a in service.clinician_day(principal, day)]
