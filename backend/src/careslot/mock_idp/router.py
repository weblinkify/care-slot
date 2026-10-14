"""Token endpoint of the mock IdP with synthetic demo users."""

import hashlib
import hmac
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from careslot.shared.errors import PROBLEM_RESPONSES, AuthenticationError
from careslot.shared.principal import Role
from careslot.shared.ratelimit import RateLimiter
from careslot.shared.security import TOKEN_TTL, issue_token

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

# 5 failed attempts per minute per (client, username): slows online guessing to a crawl
# while a real user who mistypes twice is unaffected.
login_limiter = RateLimiter(limit=5, window_seconds=60)


class TokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 - OAuth2 token type, not a secret
    expires_in: int
    role: Role
    display_name: str


router = APIRouter(prefix="/auth", tags=["mock identity provider"])


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Exchange demo credentials for an access token (mock IdP, non-production only)",
    responses={401: PROBLEM_RESPONSES[401], 429: {"description": "Too many attempts"}},
)
def token(body: TokenRequest, request: Request) -> TokenResponse:
    client = request.client.host if request.client else "unknown"
    limiter_key = f"{client}:{body.username.lower()}"
    login_limiter.check(limiter_key)  # once blocked, even the right password is refused

    user = DEMO_USERS.get(body.username.lower())
    # Always run the KDF so response time does not reveal whether the username exists.
    password_ok = hmac.compare_digest(_hash(body.password), _DEMO_HASH)
    if user is None or not password_ok:
        login_limiter.hit(limiter_key)
        raise AuthenticationError("Invalid username or password")

    return TokenResponse(
        access_token=issue_token(user.subject, user.role),
        expires_in=int(TOKEN_TTL.total_seconds()),
        role=user.role,
        display_name=user.display_name,
    )
