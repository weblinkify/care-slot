"""Booking flow through HTTP + real PostgreSQL."""

import threading
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from careslot.modules.scheduling.domain.model import (
    Appointment,
    Slot,
    SlotUnavailableError,
)
from careslot.modules.scheduling.infrastructure.models import ClinicianRow, ClinicRow, SlotRow
from careslot.modules.scheduling.infrastructure.repository import SqlSchedulingRepository
from careslot.shared import db as db_module
from careslot.shared.principal import Role
from tests.integration.conftest import bearer, future

pytestmark = pytest.mark.integration


@dataclass
class World:
    clinician_id: UUID
    slot_ids: list[UUID]


@pytest.fixture
def world(session: Session) -> World:
    clinic = ClinicRow(id=uuid4(), name="Synthetic Health Centre", timezone="Europe/Helsinki")
    clinician = ClinicianRow(
        id=uuid4(), clinic_id=clinic.id, display_name="Dr. Synthetic", specialty="General"
    )
    slots = [
        SlotRow(
            id=uuid4(),
            clinician_id=clinician.id,
            starts_at=future(24 + i),
            ends_at=future(24 + i) + timedelta(minutes=30),
        )
        for i in range(3)
    ]
    session.add(clinic)
    session.flush()
    session.add(clinician)
    session.flush()
    session.add_all(slots)
    session.commit()
    return World(clinician_id=clinician.id, slot_ids=[s.id for s in slots])


def test_book_list_reschedule_cancel(client: TestClient, world: World) -> None:
    me = bearer(uuid4(), Role.PATIENT)

    booked = client.post(
        "/api/v1/appointments", json={"slot_id": str(world.slot_ids[0])}, headers=me
    )
    assert booked.status_code == 201, booked.text
    appt_id = booked.json()["id"]

    mine = client.get("/api/v1/appointments", headers=me).json()
    assert [a["id"] for a in mine] == [appt_id]

    moved = client.post(
        f"/api/v1/appointments/{appt_id}/reschedule",
        json={"slot_id": str(world.slot_ids[1])},
        headers=me,
    )
    assert moved.status_code == 200
    assert moved.json()["slot_id"] == str(world.slot_ids[1])

    cancelled = client.post(f"/api/v1/appointments/{appt_id}/cancel", headers=me)
    assert cancelled.json()["status"] == "cancelled"

    window = {"from": future(0).isoformat(), "to": future(72).isoformat()}
    free = client.get(f"/api/v1/clinicians/{world.clinician_id}/slots", params=window, headers=me)
    assert {s["id"] for s in free.json()} == {str(s) for s in world.slot_ids}


def test_double_booking_returns_problem_json(client: TestClient, world: World) -> None:
    body = {"slot_id": str(world.slot_ids[0])}
    assert (
        client.post(
            "/api/v1/appointments", json=body, headers=bearer(uuid4(), Role.PATIENT)
        ).status_code
        == 201
    )

    second = client.post("/api/v1/appointments", json=body, headers=bearer(uuid4(), Role.PATIENT))
    assert second.status_code == 409
    assert second.headers["content-type"] == "application/problem+json"
    assert second.json()["type"].endswith("/slot-unavailable")


def test_concurrent_bookings_cannot_both_win(database_url: str, world: World) -> None:
    """Two transactions both pass the application-level "is it free?" check at the same time.
    Only the partial unique index stops the second one. This is the race that the
    application check alone cannot prevent."""
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def attempt() -> None:
        with db_module.get_session_factory()() as s:
            repo = SqlSchedulingRepository(s)
            row = s.get_one(SlotRow, world.slot_ids[0])
            slot = Slot(
                id=row.id,
                clinician_id=row.clinician_id,
                starts_at=row.starts_at,
                ends_at=row.ends_at,
            )
            assert not repo.is_slot_booked(slot.id)
            barrier.wait()  # both have now seen the slot as free
            try:
                repo.add(Appointment.book(patient_id=uuid4(), slot=slot, now=future(0)))
                s.commit()
                outcomes.append("booked")
            except SlotUnavailableError:
                s.rollback()
                outcomes.append("rejected")

    threads = [threading.Thread(target=attempt) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert sorted(outcomes) == ["booked", "rejected"]


def test_requests_without_token_are_rejected(client: TestClient) -> None:
    resp = client.get("/api/v1/clinics")
    assert resp.status_code == 401
    assert resp.json()["type"].endswith("/unauthenticated")


def test_tampered_token_is_rejected(client: TestClient) -> None:
    token = bearer(uuid4(), Role.PATIENT)["Authorization"]
    resp = client.get("/api/v1/clinics", headers={"Authorization": token[:-4] + "AAAA"})
    assert resp.status_code == 401


def test_unknown_fields_are_rejected(client: TestClient, world: World) -> None:
    # Mass-assignment attempt: a patient tries to set someone else's patient_id.
    resp = client.post(
        "/api/v1/appointments",
        json={"slot_id": str(world.slot_ids[0]), "patient_id": str(uuid4())},
        headers=bearer(uuid4(), Role.PATIENT),
    )
    assert resp.status_code == 422
    assert str(world.slot_ids[0]) not in resp.text  # input is not echoed back


def test_clinician_schedule(client: TestClient, world: World) -> None:
    client.post(
        "/api/v1/appointments",
        json={"slot_id": str(world.slot_ids[0])},
        headers=bearer(uuid4(), Role.PATIENT),
    )
    day = future(24).date().isoformat()
    resp = client.get(
        "/api/v1/clinicians/me/schedule",
        params={"day": day},
        headers=bearer(world.clinician_id, Role.CLINICIAN),
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_patient_cannot_read_clinician_schedule(client: TestClient) -> None:
    resp = client.get(
        "/api/v1/clinicians/me/schedule",
        params={"day": "2026-03-02"},
        headers=bearer(uuid4(), Role.PATIENT),
    )
    assert resp.status_code == 403


def test_cancel_with_a_reason_from_the_closed_list(client: TestClient, world: World) -> None:
    me = bearer(uuid4(), Role.PATIENT)
    appt = client.post(
        "/api/v1/appointments", json={"slot_id": str(world.slot_ids[0])}, headers=me
    ).json()

    resp = client.post(
        f"/api/v1/appointments/{appt['id']}/cancel",
        json={"reason": "scheduling-conflict"},
        headers=me,
    )
    assert resp.status_code == 200
    assert resp.json()["cancellation_reason"] == "scheduling-conflict"


def test_free_text_reasons_are_rejected(client: TestClient, world: World) -> None:
    # Data minimisation: a text box would collect health details we must not store.
    me = bearer(uuid4(), Role.PATIENT)
    appt = client.post(
        "/api/v1/appointments", json={"slot_id": str(world.slot_ids[0])}, headers=me
    ).json()
    resp = client.post(
        f"/api/v1/appointments/{appt['id']}/cancel",
        json={"reason": "my back pain got worse"},
        headers=me,
    )
    assert resp.status_code == 422
    assert "back pain" not in resp.text  # and the input is not echoed back


def test_cancel_without_a_body_still_works_for_existing_clients(
    client: TestClient, world: World
) -> None:
    me = bearer(uuid4(), Role.PATIENT)
    appt = client.post(
        "/api/v1/appointments", json={"slot_id": str(world.slot_ids[0])}, headers=me
    ).json()
    resp = client.post(f"/api/v1/appointments/{appt['id']}/cancel", headers=me)
    assert resp.status_code == 200
    assert resp.json()["cancellation_reason"] is None
