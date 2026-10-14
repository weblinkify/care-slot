"""Audit bounded context: append-only, hash-chained record of access to patient data.

PUBLIC INTERFACE. Other modules use `get_audit_sink` (a FastAPI dependency) to obtain an
`AuditSink` bound to the current request's transaction, or `make_audit_sink` outside HTTP
(jobs, seed). They never touch audit tables directly.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from careslot.modules.audit.application.services import AuditService
from careslot.modules.audit.infrastructure.repository import SqlAuditRepository
from careslot.shared.audit import AuditSink
from careslot.shared.clock import Clock, system_clock
from careslot.shared.db import get_session


def make_audit_sink(session: Session, clock: Clock = system_clock) -> AuditSink:
    return AuditService(SqlAuditRepository(session), clock).record


def get_audit_sink(session: Annotated[Session, Depends(get_session)]) -> AuditSink:
    return make_audit_sink(session)


__all__ = ["get_audit_sink", "make_audit_sink"]
