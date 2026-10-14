"""Access logs are structured, correlated with traces and free of personal data."""

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from careslot.main import create_app
from careslot.shared.config import Settings
from careslot.shared.principal import Role
from careslot.shared.security import issue_token


def access_lines(out: str) -> list[dict[str, object]]:
    lines = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
    return [line for line in lines if line.get("event") == "http.request"]


def test_access_log_uses_route_template_and_trace_id(capsys: pytest.CaptureFixture[str]) -> None:
    client = TestClient(create_app(Settings(environment="test")), raise_server_exceptions=False)
    patient_id = uuid4()
    token = issue_token(uuid4(), Role.CLINICIAN)
    client.get(
        f"/api/v1/patients/{patient_id}?reason=treatment",
        headers={"Authorization": f"Bearer {token}"},
    )

    out = capsys.readouterr().out
    [line] = access_lines(out)
    assert line["route"] == "/api/v1/patients/{patient_id}"
    assert len(str(line["trace_id"])) == 32
    assert str(patient_id) not in out  # no ids from the URL
    assert "treatment" not in out  # no query strings
    assert token not in out


def test_probes_are_not_access_logged(capsys: pytest.CaptureFixture[str]) -> None:
    TestClient(create_app(Settings(environment="test"))).get("/health")
    assert access_lines(capsys.readouterr().out) == []


def test_static_routes_win_over_parameterised_ones(capsys: pytest.CaptureFixture[str]) -> None:
    client = TestClient(create_app(Settings(environment="test")), raise_server_exceptions=False)
    client.get("/api/v1/patients/me")  # 401 without a token - still logged with its template
    [line] = access_lines(capsys.readouterr().out)
    assert line["route"] == "/api/v1/patients/me"
