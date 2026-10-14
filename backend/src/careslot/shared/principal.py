"""Who is calling. Produced by authentication (`shared.security`), consumed by use cases.

Use cases receive a `Principal`, not a token or a request, so authorisation rules are plain
Python that can be unit-tested without HTTP.
"""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class Role(StrEnum):
    PATIENT = "patient"
    CLINICIAN = "clinician"
    ADMIN = "admin"


@dataclass(frozen=True)
class Principal:
    # For patients and clinicians the subject *is* their patient/clinician id (ADR-0006).
    subject: UUID
    role: Role

    def is_patient(self, patient_id: UUID) -> bool:
        return self.role is Role.PATIENT and self.subject == patient_id
