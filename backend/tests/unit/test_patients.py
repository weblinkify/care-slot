"""Patients domain and use cases."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from careslot.modules.patients.application.services import PatientNotFoundError, PatientService
from careslot.modules.patients.domain.model import (
    ERASED_NAME,
    InvalidIdentityCodeError,
    Patient,
    PatientAlreadyErasedError,
    PersonalIdentityCode,
)
from careslot.shared.audit import AccessReason
from careslot.shared.errors import BusinessRuleError, ForbiddenError
from careslot.shared.events import DomainEvent
from careslot.shared.principal import Principal, Role
from tests.fakes import RecordingAudit

NOW = datetime(2026, 3, 2, 8, 0, tzinfo=UTC)
CHECK = "0123456789ABCDEFHJKLMNPRSTUVWXY"


def synthetic_code(birth: str = "010190", individual: int = 900) -> str:
    return f"{birth}-{individual}{CHECK[int(f'{birth}{individual}') % 31]}"


# --- identity code value object -------------------------------------------------------


def test_valid_synthetic_code_parses_and_masks() -> None:
    code = PersonalIdentityCode.parse(synthetic_code(), synthetic_only=True)
    assert code.masked() == "010190-****"
    assert synthetic_code() not in repr(code)  # never leaks through logs/tracebacks


@pytest.mark.parametrize("raw", ["", "010190900X", "010190-900Z", "1234567-890A"])
def test_malformed_or_bad_checksum_is_rejected(raw: str) -> None:
    with pytest.raises(InvalidIdentityCodeError):
        PersonalIdentityCode.parse(raw, synthetic_only=False)


def test_real_range_codes_are_rejected_outside_production() -> None:
    real_range = synthetic_code(individual=123)  # valid checksum, but not in 900-999
    with pytest.raises(InvalidIdentityCodeError, match="synthetic"):
        PersonalIdentityCode.parse(real_range, synthetic_only=True)
    assert PersonalIdentityCode.parse(real_range, synthetic_only=False)


# --- erasure ----------------------------------------------------------------------------


def make_patient() -> Patient:
    return Patient(
        id=uuid4(),
        full_name="Test Person",
        identity_code=PersonalIdentityCode(synthetic_code()),
        created_at=NOW,
    )


def test_erase_anonymises_and_emits_event() -> None:
    p = make_patient()
    p.erase(NOW)
    assert (p.full_name, p.identity_code, p.erased_at) == (ERASED_NAME, None, NOW)
    assert [e.name for e in p.pending_events] == ["PatientErased"]


def test_cannot_erase_twice() -> None:
    p = make_patient()
    p.erase(NOW)
    with pytest.raises(PatientAlreadyErasedError):
        p.erase(NOW)


# --- use cases --------------------------------------------------------------------------


class FakeRepo:
    def __init__(self, *patients: Patient) -> None:
        self.items = {p.id: p for p in patients}

    def get(self, patient_id: UUID) -> Patient | None:
        return self.items.get(patient_id)

    def find_by_identity_code(self, code: PersonalIdentityCode) -> Patient | None:
        return next((p for p in self.items.values() if p.identity_code == code), None)

    def add(self, patient: Patient) -> None:
        self.items[patient.id] = patient

    def save(self, patient: Patient) -> None:
        self.items[patient.id] = patient


@pytest.fixture
def patient() -> Patient:
    return make_patient()


@pytest.fixture
def audit() -> RecordingAudit:
    return RecordingAudit()


def service(patient: Patient, audit: RecordingAudit, relationship: bool = True) -> PatientService:
    events: list[DomainEvent] = []
    return PatientService(
        repo=FakeRepo(patient),
        audit=audit,
        care_relationship=lambda _c, _p: relationship,
        publish=events.append,
        clock=lambda: NOW,
    )


def test_patient_reads_own_record_and_it_is_audited(
    patient: Patient, audit: RecordingAudit
) -> None:
    me = Principal(subject=patient.id, role=Role.PATIENT)
    assert service(patient, audit).get_own_record(me).id == patient.id
    assert audit.actions == ["patient.read"]
    assert audit.records[0].reason is AccessReason.SELF_SERVICE


def test_clinician_with_relationship_and_reason_is_audited_with_that_reason(
    patient: Patient, audit: RecordingAudit
) -> None:
    clinician = Principal(subject=uuid4(), role=Role.CLINICIAN)
    service(patient, audit).get_for_clinician(clinician, patient.id, AccessReason.TREATMENT)
    assert audit.records[0].reason is AccessReason.TREATMENT
    assert audit.records[0].actor == clinician


def test_clinician_without_care_relationship_gets_404_and_nothing_is_read(
    patient: Patient, audit: RecordingAudit
) -> None:
    clinician = Principal(subject=uuid4(), role=Role.CLINICIAN)
    with pytest.raises(PatientNotFoundError):
        service(patient, audit, relationship=False).get_for_clinician(
            clinician, patient.id, AccessReason.TREATMENT
        )
    assert audit.records == []


def test_clinician_needs_a_clinical_reason(patient: Patient, audit: RecordingAudit) -> None:
    clinician = Principal(subject=uuid4(), role=Role.CLINICIAN)
    with pytest.raises(BusinessRuleError):
        service(patient, audit).get_for_clinician(clinician, patient.id, AccessReason.AUDIT_REVIEW)


@pytest.mark.parametrize("role", [Role.ADMIN, Role.PATIENT])
def test_only_clinicians_use_the_clinical_view(
    patient: Patient, audit: RecordingAudit, role: Role
) -> None:
    with pytest.raises(ForbiddenError):
        service(patient, audit).get_for_clinician(
            Principal(subject=uuid4(), role=role), patient.id, AccessReason.TREATMENT
        )
