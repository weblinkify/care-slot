"""Authentication, mock IdP and HTTP hardening. Mostly negative tests."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from careslot.main import create_app
from careslot.mock_idp.router import (
    DEMO_PASSWORD,
    DEMO_USERS,
    REFRESH_COOKIE,
    issue_refresh_token,
)
from careslot.shared import security
from careslot.shared.config import Settings, get_settings
from careslot.shared.errors import AuthenticationError
from careslot.shared.principal import Role
from careslot.shared.security import decode_token, issue_token


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(Settings(environment="test")))


def login(client: TestClient, username: str, password: str = DEMO_PASSWORD) -> Any:
    return client.post("/api/v1/auth/token", json={"username": username, "password": password})


def test_demo_user_gets_a_verifiable_token(client: TestClient) -> None:
    resp = login(client, "aino")
    assert resp.status_code == 200
    body = resp.json()
    principal = decode_token(body["access_token"])
    assert principal.role is Role.PATIENT
    assert body["expires_in"] == 900


def test_successful_logins_do_not_consume_the_failure_budget(client: TestClient) -> None:
    for _ in range(10):
        assert login(client, "aino").status_code == 200


@pytest.mark.parametrize(("username", "password"), [("aino", "wrong"), ("nobody", DEMO_PASSWORD)])
def test_bad_credentials_give_identical_errors(
    client: TestClient, username: str, password: str
) -> None:
    # Same status and message for unknown user and wrong password: no username enumeration.
    resp = login(client, username, password)
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid username or password"


def test_login_is_rate_limited(client: TestClient) -> None:
    for _ in range(5):
        assert login(client, "aino", "wrong").status_code == 401
    blocked = login(client, "aino")  # even the correct password is refused now
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0


def refresh(client: TestClient, cookie: str | None) -> Any:
    # Set per request: the cookie is Secure, so the http:// test client would not resend it.
    client.cookies.clear()
    if cookie is not None:
        client.cookies.set(REFRESH_COOKIE, cookie)
    return client.post("/api/v1/auth/refresh")


def test_login_sets_a_locked_down_refresh_cookie(client: TestClient) -> None:
    set_cookie = login(client, "aino").headers["set-cookie"].lower()
    assert set_cookie.startswith(f"{REFRESH_COOKIE}=")
    for attribute in ("httponly", "secure", "samesite=strict", "path=/api/v1/auth"):
        assert attribute in set_cookie
    assert "max-age" not in set_cookie and "expires" not in set_cookie  # session cookie


def test_refresh_cookie_survives_a_reload_as_a_new_access_token(client: TestClient) -> None:
    cookie = login(client, "dr.aava").cookies[REFRESH_COOKIE]
    resp = refresh(client, cookie)
    assert resp.status_code == 200
    body = resp.json()
    assert decode_token(body["access_token"]).subject == DEMO_USERS["dr.aava"].subject
    assert body["role"] == "clinician"
    assert body["display_name"] == "Dr. Aava Example"


def test_refresh_without_a_cookie_is_rejected(client: TestClient) -> None:
    resp = refresh(client, None)
    assert resp.status_code == 401
    assert resp.headers["content-type"] == "application/problem+json"


def test_access_token_is_not_accepted_as_a_refresh_token(client: TestClient) -> None:
    access = login(client, "aino").json()["access_token"]
    assert refresh(client, access).status_code == 401


def test_refresh_token_is_not_accepted_as_an_access_token(client: TestClient) -> None:
    cookie = login(client, "aino").cookies[REFRESH_COOKIE]
    with pytest.raises(AuthenticationError):
        decode_token(cookie)
    client.cookies.clear()
    resp = client.get("/api/v1/clinics", headers={"Authorization": f"Bearer {cookie}"})
    assert resp.status_code == 401


def test_expired_refresh_token_is_rejected(client: TestClient) -> None:
    stale = issue_refresh_token(
        DEMO_USERS["aino"].subject, now=datetime.now(UTC) - timedelta(hours=9)
    )
    assert refresh(client, stale).status_code == 401


def test_logout_clears_the_refresh_cookie(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 204
    set_cookie = resp.headers["set-cookie"].lower()
    assert set_cookie.startswith(f'{REFRESH_COOKIE}=""') or f"{REFRESH_COOKIE}=;" in set_cookie
    assert "max-age=0" in set_cookie
    assert "path=/api/v1/auth" in set_cookie


def test_mock_idp_is_not_mounted_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(Settings(environment="production"))
    production = TestClient(app)
    resp = production.post("/api/v1/auth/token", json={"username": "a", "password": "b"})
    assert resp.status_code == 404
    assert production.post("/api/v1/auth/refresh").status_code == 404
    assert production.post("/api/v1/auth/logout").status_code == 404


def test_production_refuses_to_start_without_a_public_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CARESLOT_ENVIRONMENT", "production")
    get_settings.cache_clear()
    security.get_keys.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="JWT_PUBLIC_KEY"):
            security.get_keys()
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
        security.get_keys.cache_clear()


def test_expired_token_is_rejected() -> None:
    token = issue_token(uuid4(), Role.PATIENT, now=datetime.now(UTC) - timedelta(hours=1))
    with pytest.raises(AuthenticationError):
        decode_token(token)


def test_unsigned_alg_none_token_is_rejected() -> None:
    claims = {
        "sub": str(uuid4()),
        "role": "admin",
        "iss": "careslot-mock-idp",
        "aud": "careslot-api",
    }
    forged = jwt.encode(
        claims | {"exp": datetime.now(UTC) + timedelta(minutes=5)}, key=None, algorithm="none"
    )
    with pytest.raises(AuthenticationError):
        decode_token(forged)


def test_token_for_another_audience_is_rejected() -> None:
    keys = security.get_keys()
    assert keys.private_pem is not None
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "role": "patient",
            "iss": "careslot-mock-idp",
            "aud": "some-other-api",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        keys.private_pem,
        algorithm="RS256",
    )
    with pytest.raises(AuthenticationError):
        decode_token(token)


def test_security_headers_on_every_response(client: TestClient) -> None:
    headers = client.get("/health").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Cache-Control"] == "no-store"
    assert headers["Content-Security-Policy"].startswith("default-src 'none'")


def test_docs_get_a_csp_that_lets_swagger_load(client: TestClient) -> None:
    csp = client.get("/api/v1/docs").headers["Content-Security-Policy"]
    assert "cdn.jsdelivr.net" in csp
