"""Authentication: verify bearer JWTs and turn them into a `Principal`.

RS256 (asymmetric) rather than HS256: the API holds only the *public* key, so a compromised
API instance cannot mint tokens. With a real identity provider the public key comes from its
JWKS endpoint; here it comes from the environment, or - only in local/test environments - an
ephemeral key pair shared with the in-process mock IdP (ADR-0006).
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Annotated, Any
from uuid import UUID

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from careslot.shared.config import get_settings
from careslot.shared.errors import AuthenticationError, ForbiddenError
from careslot.shared.principal import Principal, Role

ALGORITHM = "RS256"
TOKEN_TTL = timedelta(minutes=15)  # short-lived: limits the damage of a leaked token


@dataclass(frozen=True)
class KeyPair:
    private_pem: bytes | None  # only present where tokens are issued (mock IdP)
    public_pem: bytes


@lru_cache
def get_keys() -> KeyPair:
    settings = get_settings()
    if settings.jwt_public_key:
        private = settings.idp_private_key
        return KeyPair(
            private_pem=private.get_secret_value().encode() if private else None,
            public_pem=settings.jwt_public_key.encode(),
        )
    if settings.environment not in ("local", "test"):
        # Fail fast at startup rather than run production with a throwaway key.
        raise RuntimeError("CARESLOT_JWT_PUBLIC_KEY must be set outside local/test")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return KeyPair(
        private_pem=key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
        public_pem=key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        ),
    )


def issue_token(subject: UUID, role: Role, now: datetime | None = None) -> str:
    """Used by the mock IdP and tests only. Production tokens come from the real IdP."""
    keys = get_keys()
    if keys.private_pem is None:
        raise RuntimeError("this instance is not configured to issue tokens")
    settings = get_settings()
    now = now or datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": str(subject),
        "role": role.value,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": now + TOKEN_TTL,
    }
    return jwt.encode(claims, keys.private_pem, algorithm=ALGORITHM)


def decode_token(token: str) -> Principal:
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            get_keys().public_pem,
            algorithms=[ALGORITHM],  # pinned: never let the token choose (alg=none attacks)
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["sub", "role", "exp", "iss", "aud"]},
        )
        return Principal(subject=UUID(claims["sub"]), role=Role(claims["role"]))
    except (jwt.PyJWTError, ValueError) as exc:
        raise AuthenticationError("Invalid or expired token") from exc


_bearer = HTTPBearer(auto_error=False)


def get_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    if credentials is None:
        raise AuthenticationError()
    return decode_token(credentials.credentials)


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]


def require_role(*roles: Role) -> Any:
    """Route-level coarse check. Fine-grained ownership checks live in the use cases."""

    def dependency(principal: CurrentPrincipal) -> Principal:
        if principal.role not in roles:
            raise ForbiddenError()
        return principal

    return Depends(dependency)
