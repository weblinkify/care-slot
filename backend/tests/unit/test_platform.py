"""Platform-level behaviour: error contract, probes, log redaction."""

from datetime import datetime

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from careslot.main import create_app
from careslot.shared.db import UTCDateTime
from careslot.shared.errors import ConflictError
from careslot.shared.logging import REDACTED, redact_sensitive


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    router = APIRouter()

    @router.get("/boom")
    def boom() -> None:
        raise ConflictError("slot already taken")

    @router.get("/crash")
    def crash() -> None:
        raise RuntimeError("secret internals")

    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


def test_health_is_dependency_free(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok", "checks": {}}


def test_domain_errors_are_rfc7807(client: TestClient) -> None:
    resp = client.get("/boom")
    assert resp.status_code == 409
    assert resp.headers["content-type"] == "application/problem+json"
    assert resp.json() == {
        "type": "https://careslot.example/problems/conflict",
        "title": "Conflict with current state",
        "status": 409,
        "detail": "slot already taken",
        "instance": "/boom",
    }


def test_unhandled_errors_do_not_leak_internals(client: TestClient) -> None:
    resp = client.get("/crash")
    assert resp.status_code == 500
    assert "secret internals" not in resp.text


def test_unknown_route_is_problem_json(client: TestClient) -> None:
    resp = client.get("/nope")
    assert resp.status_code == 404
    assert resp.json()["type"].endswith("/not-found")


def test_log_redaction_masks_personal_data() -> None:
    event = {"event": "patient.viewed", "email": "a@b.c", "Personal_Identity_Code": "x", "id": 1}
    out = redact_sensitive(None, "info", event)
    assert out == {
        "event": "patient.viewed",
        "email": REDACTED,
        "Personal_Identity_Code": REDACTED,
        "id": 1,
    }


def test_naive_datetimes_are_rejected() -> None:
    with pytest.raises(ValueError, match="naive"):
        UTCDateTime().process_bind_param(datetime(2026, 1, 1, 9, 0), None)  # noqa: DTZ001
