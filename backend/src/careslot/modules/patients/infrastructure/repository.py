from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from careslot.modules.patients.domain.model import Patient, PersonalIdentityCode
from careslot.modules.patients.infrastructure.models import PatientRow
from careslot.shared import crypto


def _aad(patient_id: UUID) -> str:
    # Binds the ciphertext to this exact row and column (see shared.crypto).
    return f"pat_patients.identity_code:{patient_id}"


class SqlPatientRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, patient_id: UUID) -> Patient | None:
        row = self._session.get(PatientRow, patient_id)
        return self._to_domain(row) if row else None

    def find_by_identity_code(self, code: PersonalIdentityCode) -> Patient | None:
        row = self._session.scalar(
            select(PatientRow).where(
                PatientRow.identity_code_index == crypto.blind_index(code.value)
            )
        )
        return self._to_domain(row) if row else None

    def add(self, patient: Patient) -> None:
        row = PatientRow(id=patient.id, created_at=patient.created_at)
        self._apply(row, patient)
        self._session.add(row)
        self._session.flush()

    def save(self, patient: Patient) -> None:
        self._apply(self._session.get_one(PatientRow, patient.id), patient)
        self._session.flush()

    @staticmethod
    def _apply(row: PatientRow, patient: Patient) -> None:
        row.full_name = patient.full_name
        row.erased_at = patient.erased_at
        if patient.identity_code is None:
            row.identity_code_ciphertext = None
            row.identity_code_index = None
        else:
            row.identity_code_ciphertext = crypto.encrypt(
                patient.identity_code.value, _aad(patient.id)
            )
            row.identity_code_index = crypto.blind_index(patient.identity_code.value)

    @staticmethod
    def _to_domain(row: PatientRow) -> Patient:
        code = None
        if row.identity_code_ciphertext is not None:
            plaintext = crypto.decrypt(row.identity_code_ciphertext, _aad(row.id))
            # Already validated when stored; re-wrapping without the synthetic-only guard means
            # a production record never becomes unreadable because of a test-data rule.
            code = PersonalIdentityCode(plaintext)
        return Patient(
            id=row.id,
            full_name=row.full_name,
            identity_code=code,
            created_at=row.created_at,
            erased_at=row.erased_at,
        )
