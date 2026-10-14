"""GDPR flows end to end on real PostgreSQL: consent, right to erasure, retention."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from careslot.jobs import retention
from careslot.modules.consent.infrastructure.models import ConsentDecisionRow
from careslot.modules.scheduling.infrastructure.models import (
    AppointmentRow,
    ClinicianRow,
    ClinicRow,
    SlotRow,
)
from careslot.shared.principal import Role
from tests.integration.conftest import bearer, future, synthetic_code
from tests.integration.test_patients_and_audit import register

pytestmark = pytest.mark.integration


def clinic(session: Session, slot_starts: list[datetime]) -> list[UUID]:
    c = ClinicRow(id=uuid4(), name="Synthetic Health Centre", timezone="Europe/Helsinki")
    doc = ClinicianRow(id=uuid4(), clinic_id=c.id, display_name="Dr. Y", specialty="GP")
    session.add(c)
    session.flush()
    session.add(doc)
    session.flush()
    slots = [
        SlotRow(id=uuid4(), clinician_id=doc.id, starts_at=t, ends_at=t + timedelta(minutes=30))
        for t in slot_starts
    ]
    session.add_all(slots)
    session.commit()
    return [s.id for s in slots]


def test_consent_round_trip_is_provable(client: TestClient, session: Session) -> None:
    me = bearer(register(session, synthetic_code()), Role.PATIENT)

    assert (
        client.put("/api/v1/consents/research", json={"granted": True}, headers=me).status_code
        == 200
    )
    client.put("/api/v1/consents/research", json={"granted": False}, headers=me)

    overview = client.get("/api/v1/consents", headers=me).json()
    research = next(c for c in overview["current"] if c["purpose"] == "research")
    assert research["granted"] is False
    assert [h["granted"] for h in overview["history"]] == [False, True]  # newest first


def test_unknown_purpose_is_rejected(client: TestClient, session: Session) -> None:
    me = bearer(register(session, synthetic_code()), Role.PATIENT)
    resp = client.put("/api/v1/consents/marketing", json={"granted": True}, headers=me)
    assert resp.status_code == 422


def test_right_to_erasure_end_to_end(client: TestClient, session: Session) -> None:
    patient_id = register(session, synthetic_code())
    me = bearer(patient_id, Role.PATIENT)
    slot_ids = clinic(session, [future(48)])
    appt = client.post(
        "/api/v1/appointments", json={"slot_id": str(slot_ids[0])}, headers=me
    ).json()
    client.put("/api/v1/consents/ai-summaries", json={"granted": True}, headers=me)

    # Missing confirmation is refused.
    assert client.post("/api/v1/patients/me/erasure", json={}, headers=me).status_code == 422
    resp = client.post("/api/v1/patients/me/erasure", json={"confirm": True}, headers=me)
    assert resp.status_code == 200

    # Identity is gone (ciphertext and blind index too), the row and id remain.
    row = session.execute(
        text(
            "SELECT full_name, identity_code_ciphertext, identity_code_index, erased_at"
            " FROM pat_patients WHERE id = :id"
        ),
        {"id": patient_id},
    ).one()
    assert row[0] == "Erased patient" and row[1] is None and row[2] is None and row[3] is not None

    # Other modules reacted to PatientErased in the same transaction.
    session.expire_all()
    assert session.get_one(AppointmentRow, UUID(appt["id"])).status == "cancelled"
    assert (
        session.scalar(
            select(func.count())
            .select_from(ConsentDecisionRow)
            .where(ConsentDecisionRow.patient_id == patient_id)
        )
        == 0
    )

    # The freed slot is bookable again.
    window = {"from": future(0).isoformat(), "to": future(72).isoformat()}
    doc_slots = session.get_one(SlotRow, slot_ids[0]).clinician_id
    free = client.get(f"/api/v1/clinicians/{doc_slots}/slots", params=window, headers=me).json()
    assert str(slot_ids[0]) in {s["id"] for s in free}

    # Audit history is kept and still verifies: erasure did not rewrite it.
    admin = bearer(uuid4(), Role.ADMIN)
    actions = [
        e["action"]
        for e in client.get(
            "/api/v1/audit-log", params={"patient_id": str(patient_id)}, headers=admin
        ).json()
    ]
    assert {"patient.create", "appointment.book", "patient.erase", "appointment.cancel"} <= set(
        actions
    )
    assert client.get("/api/v1/audit-log/verify", headers=admin).json()["valid"] is True

    # Erasing twice is a conflict, not a silent success.
    assert (
        client.post("/api/v1/patients/me/erasure", json={"confirm": True}, headers=me).status_code
        == 409
    )


def test_retention_job_deletes_only_expired_booking_data(session: Session) -> None:
    now = datetime.now(UTC)
    old, unused_old, recent = clinic(
        session, [now - timedelta(days=800), now - timedelta(days=900), now - timedelta(days=5)]
    )
    for slot_id in (old, recent):
        slot = session.get_one(SlotRow, slot_id)
        session.add(
            AppointmentRow(
                id=uuid4(),
                patient_id=uuid4(),
                clinician_id=slot.clinician_id,
                slot_id=slot.id,
                starts_at=slot.starts_at,
                ends_at=slot.ends_at,
                status="booked",
                created_at=slot.starts_at - timedelta(days=1),
            )
        )
    session.commit()

    assert retention.run() == (1, 2)  # 1 old appointment; its slot + the unused old slot
    assert retention.run() == (0, 0)  # idempotent
    session.expire_all()
    assert session.get(SlotRow, recent) is not None
    assert session.get(SlotRow, old) is None
    assert session.get(SlotRow, unused_old) is None


@pytest.mark.parametrize("value", [0, 1, "true", "no", None])
def test_consent_must_be_an_unambiguous_boolean(
    client: TestClient, session: Session, value: object
) -> None:
    # Found by the contract tests: lax parsing turned {"granted": 0} into a decision.
    me = bearer(register(session, synthetic_code()), Role.PATIENT)
    resp = client.put("/api/v1/consents/research", json={"granted": value}, headers=me)
    assert resp.status_code == 422
