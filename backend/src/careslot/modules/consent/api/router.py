from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from careslot.modules.audit import get_audit_sink
from careslot.modules.consent.application.services import ConsentService
from careslot.modules.consent.domain.model import ConsentPurpose, ConsentState
from careslot.modules.consent.infrastructure.repository import SqlConsentRepository
from careslot.shared.audit import AuditSink
from careslot.shared.clock import system_clock
from careslot.shared.db import get_session
from careslot.shared.errors import PROBLEM_RESPONSES
from careslot.shared.events import event_bus
from careslot.shared.principal import Role
from careslot.shared.security import CurrentPrincipal, require_role


def get_consent_service(
    session: Annotated[Session, Depends(get_session)],
    audit: Annotated[AuditSink, Depends(get_audit_sink)],
) -> ConsentService:
    return ConsentService(
        repo=SqlConsentRepository(session),
        audit=audit,
        publish=lambda event: event_bus.publish(event, session),
        clock=system_clock,
    )


Service = Annotated[ConsentService, Depends(get_consent_service)]


class ConsentStateOut(BaseModel):
    purpose: ConsentPurpose
    granted: bool
    decided_at: datetime | None
    policy_version: str | None

    @classmethod
    def of(cls, s: ConsentState) -> "ConsentStateOut":
        return cls(
            purpose=s.purpose,
            granted=s.granted,
            decided_at=s.decided_at,
            policy_version=s.policy_version,
        )


class ConsentDecisionOut(BaseModel):
    id: UUID
    purpose: ConsentPurpose
    granted: bool
    decided_at: datetime
    policy_version: str


class ConsentOverviewOut(BaseModel):
    current: list[ConsentStateOut]
    history: list[ConsentDecisionOut]


class ConsentDecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    granted: bool


router = APIRouter(
    prefix="/consents",
    tags=["consent"],
    dependencies=[require_role(Role.PATIENT)],
    responses={k: PROBLEM_RESPONSES[k] for k in (401, 403)},
)


@router.get("", response_model=ConsentOverviewOut, summary="Current consents and full history")
def overview(principal: CurrentPrincipal, service: Service) -> ConsentOverviewOut:
    current, history = service.overview(principal)
    return ConsentOverviewOut(
        current=[ConsentStateOut.of(s) for s in current],
        history=[
            ConsentDecisionOut(
                id=d.id,
                purpose=d.purpose,
                granted=d.granted,
                decided_at=d.decided_at,
                policy_version=d.policy_version,
            )
            for d in history
        ],
    )


@router.put(
    "/{purpose}",
    response_model=ConsentStateOut,
    summary="Grant or withdraw consent for one purpose (idempotent)",
)
def decide(
    purpose: ConsentPurpose, body: ConsentDecisionIn, principal: CurrentPrincipal, service: Service
) -> ConsentStateOut:
    return ConsentStateOut.of(service.decide(principal, purpose, body.granted))
