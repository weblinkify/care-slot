from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from careslot.modules.audit.application.services import MAX_PAGE, AuditQuery, AuditService
from careslot.modules.audit.domain.model import AuditEntry
from careslot.modules.audit.infrastructure.repository import SqlAuditRepository
from careslot.shared.clock import system_clock
from careslot.shared.db import get_session
from careslot.shared.errors import PROBLEM_RESPONSES
from careslot.shared.principal import Role
from careslot.shared.security import CurrentPrincipal, require_role


def get_audit_service(session: Annotated[Session, Depends(get_session)]) -> AuditService:
    return AuditService(SqlAuditRepository(session), system_clock)


Service = Annotated[AuditService, Depends(get_audit_service)]


class AuditEntryOut(BaseModel):
    id: int
    occurred_at: datetime
    actor_id: UUID | None
    actor_role: str | None
    action: str
    resource_type: str
    resource_id: str
    patient_id: UUID | None
    reason: str
    hash: str

    @classmethod
    def of(cls, e: AuditEntry) -> "AuditEntryOut":
        assert e.id is not None  # noqa: S101 - persisted entries always have an id
        return cls(
            id=e.id,
            occurred_at=e.occurred_at,
            actor_id=e.actor_id,
            actor_role=e.actor_role,
            action=e.action,
            resource_type=e.resource_type,
            resource_id=e.resource_id,
            patient_id=e.patient_id,
            reason=e.reason,
            hash=e.hash,
        )


class ChainVerificationOut(BaseModel):
    valid: bool
    entries_checked: int
    first_invalid_id: int | None


router = APIRouter(
    prefix="/audit-log",
    tags=["audit"],
    dependencies=[require_role(Role.ADMIN)],
    responses={k: PROBLEM_RESPONSES[k] for k in (401, 403)},
)


@router.get("", response_model=list[AuditEntryOut], summary="Search the audit log (newest first)")
def search(
    principal: CurrentPrincipal,
    service: Service,
    patient_id: UUID | None = None,
    actor_id: UUID | None = None,
    before_id: Annotated[
        int | None, Query(description="Keyset cursor: id of the last entry seen")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE)] = 50,
) -> list[AuditEntryOut]:
    query = AuditQuery(patient_id=patient_id, actor_id=actor_id, before_id=before_id, limit=limit)
    return [AuditEntryOut.of(e) for e in service.search(principal, query)]


@router.get(
    "/verify",
    response_model=ChainVerificationOut,
    summary="Recompute the hash chain and report the first tampered entry, if any",
)
def verify(principal: CurrentPrincipal, service: Service) -> ChainVerificationOut:
    result = service.verify(principal)
    return ChainVerificationOut(
        valid=result.valid,
        entries_checked=result.entries_checked,
        first_invalid_id=result.first_invalid_id,
    )
