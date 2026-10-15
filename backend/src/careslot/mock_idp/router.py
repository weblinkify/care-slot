"""Token endpoint of the mock IdP with synthetic demo users."""

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

import jwt
from fastapi import APIRouter, Cookie, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from careslot.shared.config import get_settings
from careslot.shared.errors import PROBLEM_RESPONSES, AuthenticationError
from careslot.shared.principal import Role
from careslot.shared.ratelimit import RateLimiter
from careslot.shared.security import ALGORITHM, TOKEN_TTL, get_keys, issue_token

# Publicly documented demo credential for synthetic accounts (README). Not a secret.
DEMO_PASSWORD = "demo-password"  # noqa: S105
_SALT = b"careslot-demo-salt"


def _hash(password: str) -> bytes:
    # scrypt from the standard library: a memory-hard KDF, no extra dependency needed.
    return hashlib.scrypt(password.encode(), salt=_SALT, n=2**14, r=8, p=1)


_DEMO_HASH = _hash(DEMO_PASSWORD)


@dataclass(frozen=True)
class DemoUser:
    subject: UUID
    role: Role
    display_name: str


# Subjects match the IDs created by `careslot.seed`.
DEMO_USERS: dict[str, DemoUser] = {
    "aino": DemoUser(UUID("a1000000-0000-4000-8000-000000000001"), Role.PATIENT, "Aino (patient)"),
    "eero": DemoUser(UUID("a1000000-0000-4000-8000-000000000002"), Role.PATIENT, "Eero (patient)"),
    "dr.aava": DemoUser(
        UUID("c1000000-0000-4000-8000-000000000001"), Role.CLINICIAN, "Dr. Aava Example"
    ),
    "admin": DemoUser(UUID("ad000000-0000-4000-8000-000000000001"), Role.ADMIN, "Admin"),
}
_USERS_BY_SUBJECT = {user.subject: user for user in DEMO_USERS.values()}

# The refresh token keeps a session alive across page reloads while the access token stays in
# memory only. It lives in an HttpOnly cookie, so script (including an XSS payload) can never
# read it, and it is scoped to the auth endpoints, so it is never sent with API calls.
# Absolute lifetime of one working shift; it is not extended on use (ADR-0012).
REFRESH_COOKIE = "careslot_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"
REFRESH_TTL = timedelta(hours=8)
_REFRESH_TYPE = "refresh"

# 5 failed attempts per minute per (client, username): slows online guessing to a crawl
# while a real user who mistypes twice is unaffected.
login_limiter = RateLimiter(limit=5, window_seconds=60)


class TokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 - OAuth2 token type, not a secret
    expires_in: int
    role: Role
    display_name: str


router = APIRouter(prefix="/auth", tags=["mock identity provider"])


def issue_refresh_token(subject: UUID, now: datetime | None = None) -> str:
    keys = get_keys()
    if keys.private_pem is None:
        raise RuntimeError("this instance is not configured to issue tokens")
    issuer = get_settings().jwt_issuer
    now = now or datetime.now(UTC)
    # Addressed to the IdP itself, not the API: `decode_token` requires the API audience, so
    # a refresh token can never be replayed as an access token.
    claims = {
        "sub": str(subject),
        "typ": _REFRESH_TYPE,
        "iss": issuer,
        "aud": issuer,
        "iat": now,
        "exp": now + REFRESH_TTL,
    }
    return jwt.encode(claims, keys.private_pem, algorithm=ALGORITHM)


def _refresh_subject(token: str) -> UUID:
    issuer = get_settings().jwt_issuer
    try:
        claims = jwt.decode(
            token,
            get_keys().public_pem,
            algorithms=[ALGORITHM],
            audience=issuer,
            issuer=issuer,
            options={"require": ["sub", "typ", "exp", "iss", "aud"]},
        )
        if claims["typ"] != _REFRESH_TYPE:
            raise ValueError("not a refresh token")
        return UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError) as exc:
        raise AuthenticationError("Session expired, please sign in again") from exc


def _token_response(user: DemoUser) -> TokenResponse:
    return TokenResponse(
        access_token=issue_token(user.subject, user.role),
        expires_in=int(TOKEN_TTL.total_seconds()),
        role=user.role,
        display_name=user.display_name,
    )


def _set_refresh_cookie(response: Response, subject: UUID) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        issue_refresh_token(subject),
        path=REFRESH_COOKIE_PATH,
        httponly=True,  # unreadable by JavaScript: an XSS payload cannot steal the session
        secure=True,  # browsers treat http://localhost as secure, so local dev still works
        # Never sent on cross-site requests, which (with JSON-only responses that CORS hides
        # from other origins) is the CSRF defence for these endpoints.
        samesite="strict",
        # No Max-Age: a session cookie, gone when the browser closes (shared computers).
    )


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Exchange demo credentials for an access token (mock IdP, non-production only)",
    responses={401: PROBLEM_RESPONSES[401], 429: PROBLEM_RESPONSES[429]},
)
def token(body: TokenRequest, request: Request, response: Response) -> TokenResponse:
    client = request.client.host if request.client else "unknown"
    limiter_key = f"{client}:{body.username.lower()}"
    login_limiter.check(limiter_key)  # once blocked, even the right password is refused

    user = DEMO_USERS.get(body.username.lower())
    # Always run the KDF so response time does not reveal whether the username exists.
    password_ok = hmac.compare_digest(_hash(body.password), _DEMO_HASH)
    if user is None or not password_ok:
        login_limiter.hit(limiter_key)
        raise AuthenticationError("Invalid username or password")

    _set_refresh_cookie(response, user.subject)
    return _token_response(user)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange the refresh cookie for a new access token (mock IdP, non-production only)",
    responses={401: PROBLEM_RESPONSES[401]},
)
def refresh(
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> TokenResponse:
    if refresh_token is None:
        raise AuthenticationError("No active session")
    # Role and name come from the user record, not the token, so changes apply on refresh.
    user = _USERS_BY_SUBJECT.get(_refresh_subject(refresh_token))
    if user is None:
        raise AuthenticationError("Session expired, please sign in again")
    return _token_response(user)


@router.post(
    "/logout",
    status_code=204,
    summary="End the session by clearing the refresh cookie (mock IdP, non-production only)",
)
def logout(response: Response) -> None:
    # The refresh token is stateless, so this cannot revoke a copy taken elsewhere; a real
    # IdP keeps server-side sessions for that (ADR-0012).
    response.delete_cookie(
        REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, httponly=True, secure=True, samesite="strict"
    )
