"""Audit port: how any module reports access to patient data.

Modules depend on this small abstraction; the `audit` module provides the implementation
(append-only, hash-chained table) and the composition root injects it. That keeps every module
free of audit storage details and makes "was this access audited?" a one-line unit-test
assertion with a recording fake.

The audit write happens in the *same transaction* as the access it describes: if the request
fails and rolls back, so does its audit row - but a successful access can never commit
without its audit entry.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from careslot.shared.principal import Principal


class AccessReason(StrEnum):
    """Why personal data was accessed (GDPR purpose limitation). Required for clinicians."""

    SELF_SERVICE = "self-service"  # patients acting on their own data
    TREATMENT = "treatment"
    APPOINTMENT_PREPARATION = "appointment-preparation"
    AUDIT_REVIEW = "audit-review"
    DATA_SUBJECT_REQUEST = "data-subject-request"  # e.g. right to erasure
    SYSTEM_JOB = "system-job"  # retention and other scheduled jobs


@dataclass(frozen=True)
class AuditRecord:
    actor: Principal | None  # None for system jobs
    action: str  # "<resource>.<verb>", e.g. "patient.read", "appointment.cancel"
    resource_type: str
    resource_id: str
    patient_id: UUID | None
    reason: AccessReason


AuditSink = Callable[[AuditRecord], None]
