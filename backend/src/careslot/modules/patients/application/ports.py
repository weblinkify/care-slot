from collections.abc import Callable
from typing import Protocol
from uuid import UUID

from careslot.modules.patients.domain.model import Patient, PersonalIdentityCode


class PatientRepository(Protocol):
    def get(self, patient_id: UUID) -> Patient | None: ...
    def find_by_identity_code(self, code: PersonalIdentityCode) -> Patient | None: ...
    def add(self, patient: Patient) -> None: ...
    def save(self, patient: Patient) -> None: ...


# "Does this clinician have (or had) an appointment with this patient?" Answered by the
# scheduling module through its public interface - patients never reads scheduling tables.
CareRelationship = Callable[[UUID, UUID], bool]
