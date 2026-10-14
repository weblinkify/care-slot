from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from careslot.modules.audit import get_audit_sink
from careslot.modules.patients.application.services import PatientService
from careslot.modules.patients.domain.model import Patient
from careslot.modules.patients.infrastructure.repository import SqlPatientRepository
from careslot.modules.scheduling import care_relationship_checker
from careslot.shared.audit import AccessReason, AuditSink
from careslot.shared.clock import system_clock
from careslot.shared.db import get_session
from careslot.shared.errors import PROBLEM_RESPONSES
from careslot.shared.events import event_bus
from careslot.shared.principal import Role
from careslot.shared.security import CurrentPrincipal, require_role


def get_patient_service(
    session: Annotated[Session, Depends(get_session)],
    audit: Annotated[AuditSink, Depends(get_audit_sink)],
) -> PatientService:
    return PatientService(
        repo=SqlPatientRepository(session),
        audit=audit,
        care_relationship=care_relationship_checker(session),
        publish=lambda event: event_bus.publish(event, session),
        clock=system_clock,
    )


Service = Annotated[PatientService, Depends(get_patient_service)]


class OwnPatientRecordOut(BaseModel):
    """What a patient sees about themselves (GDPR right of access): everything we hold."""

    id: UUID
    full_name: str
    identity_code: str | None


class PatientSummaryOut(BaseModel):
    """What a clinician sees: identity code masked - enough to confirm identity verbally."""

    id: UUID
    full_name: str
    identity_code_masked: str | None


class ErasureRequestIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    # An explicit flag in the body so a stray or replayed POST cannot erase anyone.
    confirm: Literal[True]


class ErasureResultOut(BaseModel):
    erased_at: datetime


router = APIRouter(
    prefix="/patients",
    tags=["patients"],
    responses={k: PROBLEM_RESPONSES[k] for k in (401, 403, 404)},
)


def _own(p: Patient) -> OwnPatientRecordOut:
    return OwnPatientRecordOut(
        id=p.id,
        full_name=p.full_name,
        identity_code=p.identity_code.value if p.identity_code else None,
    )


@router.get(
    "/me",
    response_model=OwnPatientRecordOut,
    summary="The calling patient's own record",
    dependencies=[require_role(Role.PATIENT)],
)
def get_me(principal: CurrentPrincipal, service: Service) -> OwnPatientRecordOut:
    return _own(service.get_own_record(principal))


@router.post(
    "/me/erasure",
    response_model=ErasureResultOut,
    summary="Right to erasure: anonymise the calling patient (irreversible)",
    responses={409: PROBLEM_RESPONSES[409]},
    dependencies=[require_role(Role.PATIENT)],
)
def erase_me(
    body: ErasureRequestIn, principal: CurrentPrincipal, service: Service
) -> ErasureResultOut:
    patient = service.erase_own_record(principal)
    assert patient.erased_at is not None  # noqa: S101 - erase() always sets it
    return ErasureResultOut(erased_at=patient.erased_at)


@router.get(
    "/{patient_id}",
    response_model=PatientSummaryOut,
    summary="Open a patient record (clinicians with a care relationship; audited with reason)",
    responses={422: PROBLEM_RESPONSES[422]},
    dependencies=[require_role(Role.CLINICIAN)],
)
def get_for_clinician(
    patient_id: UUID,
    principal: CurrentPrincipal,
    service: Service,
    reason: Annotated[
        AccessReason, Query(description="Purpose of access, recorded in the audit log")
    ],
) -> PatientSummaryOut:
    p = service.get_for_clinician(principal, patient_id, reason)
    return PatientSummaryOut(
        id=p.id,
        full_name=p.full_name,
        identity_code_masked=p.identity_code.masked() if p.identity_code else None,
    )
