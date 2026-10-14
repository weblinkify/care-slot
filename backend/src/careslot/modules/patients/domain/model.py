"""Patients domain.

Data minimisation by design: a patient here is an id, a display name and a personal identity
code - nothing else. No address, phone, email or free-text notes: the booking service does not
need them, so it does not collect them (GDPR art. 5(1)(c)).
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from careslot.modules.patients.domain.events import PatientErased
from careslot.shared.errors import BusinessRuleError, ConflictError
from careslot.shared.events import DomainEvent

_PIC_PATTERN = re.compile(r"^(\d{6})([-+ABCDEFYXWVU])(\d{3})([0-9A-Y])$")
_CHECK_CHARS = "0123456789ABCDEFHJKLMNPRSTUVWXY"
ERASED_NAME = "Erased patient"


class InvalidIdentityCodeError(BusinessRuleError):
    code = "invalid-identity-code"
    title = "Invalid personal identity code"


class PatientAlreadyErasedError(ConflictError):
    code = "patient-erased"
    title = "Patient has been erased"


@dataclass(frozen=True)
class PersonalIdentityCode:
    """Finnish personal identity code (henkilötunnus): DDMMYY, century sign, individual
    number, check character.

    Synthetic-data guard: individual numbers 900-999 are reserved for temporary identifiers
    and are never issued to real people. Outside production we *only* accept that range, so
    seed data and tests cannot collide with a real person even by accident.
    """

    value: str

    @classmethod
    def parse(cls, raw: str, *, synthetic_only: bool) -> "PersonalIdentityCode":
        candidate = raw.strip().upper()
        match = _PIC_PATTERN.match(candidate)
        if not match:
            raise InvalidIdentityCodeError("Expected format DDMMYYCNNNX.")
        birth, _century, individual, check = match.groups()
        if _CHECK_CHARS[int(birth + individual) % 31] != check:
            raise InvalidIdentityCodeError("Check character does not match.")
        if synthetic_only and int(individual) < 900:
            raise InvalidIdentityCodeError(
                "Only synthetic identity codes (individual number 900-999) are allowed here."
            )
        return cls(candidate)

    def masked(self) -> str:
        """Birth date part only, e.g. `010190-****`: enough to confirm identity verbally."""
        return f"{self.value[:7]}****"

    def __repr__(self) -> str:  # never leak the full code through logs or tracebacks
        return f"PersonalIdentityCode({self.masked()})"


@dataclass
class Patient:
    id: UUID
    full_name: str
    identity_code: PersonalIdentityCode | None
    created_at: datetime
    erased_at: datetime | None = None
    pending_events: list[DomainEvent] = field(default_factory=list, repr=False, compare=False)

    @property
    def is_erased(self) -> bool:
        return self.erased_at is not None

    def erase(self, now: datetime) -> None:
        """Right to erasure (GDPR art. 17) by anonymisation.

        The row stays (other modules and the audit log refer to the id) but everything that
        identifies the person is removed. The id is a random UUID, so once the name and
        identity code are gone it no longer links to a natural person.
        """
        if self.is_erased:
            raise PatientAlreadyErasedError()
        self.full_name = ERASED_NAME
        self.identity_code = None
        self.erased_at = now
        self.pending_events.append(PatientErased(patient_id=self.id))
