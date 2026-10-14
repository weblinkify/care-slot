"""Patients encryption + audit log against real PostgreSQL."""

import threading
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from careslot.modules.audit import make_audit_sink
from careslot.modules.patients.application.services import PatientService
from careslot.modules.patients.domain.model import PersonalIdentityCode
from careslot.modules.patients.infrastructure.repository import SqlPatientRepository
from careslot.modules.scheduling.infrastructure.models import ClinicianRow, ClinicRow, SlotRow
from careslot.shared import db as db_module
from careslot.shared.audit import AccessReason, AuditRecord
from careslot.shared.clock import system_clock
from careslot.shared.errors import ConflictError
from careslot.shared.principal import Principal, Role
from tests.integration.conftest import bearer, future, synthetic_code

pytestmark = pytest.mark.integration


def register(session: Session, code: str, name: str = "Synthetic Person") -> UUID:
    service = PatientService(
        repo=SqlPatientRepository(session),
        audit=make_audit_sink(session),
        care_relationship=lambda _c, _p: False,
        publish=lambda _e: None,
        clock=system_clock,
    )
    patient_id = uuid4()
    service.register(patient_id, name, PersonalIdentityCode.parse(code, synthetic_only=True))
    session.commit()
    return patient_id


def clinic_with_slot(session: Session) -> tuple[UUID, UUID]:
    clinic = ClinicRow(id=uuid4(), name="Synthetic Health Centre", timezone="Europe/Helsinki")
    clinician = ClinicianRow(id=uuid4(), clinic_id=clinic.id, display_name="Dr. X", specialty="GP")
    slot = SlotRow(
        id=uuid4(),
        clinician_id=clinician.id,
        starts_at=future(30),
        ends_at=future(30) + timedelta(minutes=30),
    )
    session.add(clinic)
    session.flush()
    session.add(clinician)
    session.flush()
    session.add(slot)
    session.commit()
    return clinician.id, slot.id


# --- encryption at rest -----------------------------------------------------------------


def test_identity_code_is_not_readable_at_rest(session: Session) -> None:
    code = synthetic_code()
    patient_id = register(session, code)
    raw = session.execute(
        text(
            "SELECT identity_code_ciphertext, identity_code_index FROM pat_patients WHERE id = :id"
        ),
        {"id": patient_id},
    ).one()
    assert code.encode() not in raw[0]
    assert code not in raw[1]


def test_identity_codes_are_unique_via_blind_index(session: Session) -> None:
    register(session, synthetic_code())
    with pytest.raises(ConflictError):
        register(session, synthetic_code().lower())  # same code, different spelling


# --- audit log is append-only and tamper-evident ----------------------------------------


@pytest.mark.parametrize(
    "statement",
    ["UPDATE aud_entries SET reason = 'x'", "DELETE FROM aud_entries", "TRUNCATE aud_entries"],
)
def test_audit_rows_cannot_be_changed_or_removed(session: Session, statement: str) -> None:
    register(session, synthetic_code())  # writes a patient.create audit entry
    with pytest.raises(DBAPIError, match="append-only"):
        session.execute(text(statement))
    session.rollback()


def test_concurrent_appends_keep_a_single_valid_chain(client: TestClient) -> None:
    def append(n: int) -> None:
        for _ in range(n):
            with db_module.get_session_factory()() as s:
                make_audit_sink(s)(
                    AuditRecord(
                        actor=Principal(uuid4(), Role.PATIENT),
                        action="appointment.read",
                        resource_type="appointment",
                        resource_id=str(uuid4()),
                        patient_id=uuid4(),
                        reason=AccessReason.SELF_SERVICE,
                    )
                )
                s.commit()

    threads = [threading.Thread(target=append, args=(10,)) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    result = client.get("/api/v1/audit-log/verify", headers=bearer(uuid4(), Role.ADMIN)).json()
    assert result == {"valid": True, "entries_checked": 40, "first_invalid_id": None}


def test_tampering_by_a_privileged_db_user_is_detected(
    client: TestClient, session: Session
) -> None:
    for i in range(3):
        register(session, synthetic_code(individual=900 + i))

    # Simulate an attacker with enough database privileges to switch the trigger off.
    session.execute(text("ALTER TABLE aud_entries DISABLE TRIGGER USER"))
    session.execute(
        text(
            "UPDATE aud_entries SET action = 'patient.nothing'"
            " WHERE id = (SELECT min(id) + 1 FROM aud_entries)"
        )
    )
    session.execute(text("ALTER TABLE aud_entries ENABLE TRIGGER USER"))
    session.commit()

    result = client.get("/api/v1/audit-log/verify", headers=bearer(uuid4(), Role.ADMIN)).json()
    assert result["valid"] is False
    assert result["entries_checked"] == 1


# --- API: who may see what, and is it audited? -------------------------------------------


def test_patient_sees_own_full_record(client: TestClient, session: Session) -> None:
    code = synthetic_code()
    patient_id = register(session, code)
    me = client.get("/api/v1/patients/me", headers=bearer(patient_id, Role.PATIENT))
    assert me.status_code == 200
    assert me.json()["identity_code"] == code


def test_clinician_access_requires_relationship_and_is_audited_with_reason(
    client: TestClient, session: Session
) -> None:
    patient_id = register(session, synthetic_code())
    clinician_id, slot_id = clinic_with_slot(session)
    doctor = bearer(clinician_id, Role.CLINICIAN)

    # No appointment yet: indistinguishable from a non-existent patient.
    before = client.get(
        f"/api/v1/patients/{patient_id}", params={"reason": "treatment"}, headers=doctor
    )
    assert before.status_code == 404

    client.post(
        "/api/v1/appointments",
        json={"slot_id": str(slot_id)},
        headers=bearer(patient_id, Role.PATIENT),
    )
    after = client.get(
        f"/api/v1/patients/{patient_id}", params={"reason": "treatment"}, headers=doctor
    )
    assert after.status_code == 200
    assert after.json()["identity_code_masked"].endswith("****")
    assert "identity_code" not in after.json()

    log = client.get(
        "/api/v1/audit-log",
        params={"patient_id": str(patient_id)},
        headers=bearer(uuid4(), Role.ADMIN),
    ).json()
    reads = [e for e in log if e["action"] == "patient.read"]
    assert reads[0]["actor_id"] == str(clinician_id)
    assert reads[0]["reason"] == "treatment"
    assert {e["action"] for e in log} >= {"patient.create", "appointment.book", "patient.read"}


def test_clinician_must_state_a_valid_reason(client: TestClient, session: Session) -> None:
    resp = client.get(f"/api/v1/patients/{uuid4()}", headers=bearer(uuid4(), Role.CLINICIAN))
    assert resp.status_code == 422


@pytest.mark.parametrize("role", [Role.PATIENT, Role.CLINICIAN])
def test_only_admins_can_read_the_audit_log(client: TestClient, role: Role) -> None:
    assert client.get("/api/v1/audit-log", headers=bearer(uuid4(), role)).status_code == 403


def test_reading_the_audit_log_is_itself_audited(client: TestClient) -> None:
    admin = uuid4()
    client.get("/api/v1/audit-log", headers=bearer(admin, Role.ADMIN))
    log = client.get(
        "/api/v1/audit-log", params={"actor_id": str(admin)}, headers=bearer(admin, Role.ADMIN)
    ).json()
    # Both searches are logged; the second sees its own entry (written in the same transaction).
    assert [e["action"] for e in log] == ["audit.search", "audit.search"]
