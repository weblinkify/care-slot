"""Column-level envelope encryption and blind indexing (ADR-0003).

Envelope encryption:
  * every value gets its own random 256-bit data key (DEK) and is encrypted with AES-256-GCM;
  * the DEK is "wrapped" (encrypted) with a key-encryption key (KEK) and stored next to it;
  * KEKs live only in the environment / secret store (in production: a KMS-managed key).
Why: a database dump or backup alone reveals nothing; rotating a KEK means re-wrapping small
DEKs, not re-encrypting all data; and moving KEK handling to a cloud KMS changes one class.

Associated data (AAD) binds each ciphertext to its table, column and row id. Copying an
encrypted identity code onto another patient's row makes decryption fail instead of silently
"working" - integrity, not just confidentiality.

Blind index: an HMAC of the normalised value under a separate key. It lets us enforce
uniqueness and look up "patient by identity code" without decrypting every row, while the
index value is useless without the key.
"""

import base64
import hashlib
import hmac
import os
import struct
from dataclasses import dataclass
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from careslot.shared.config import get_settings

_FORMAT_VERSION = 1
_NONCE_BYTES = 12


class CryptoConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class KeyRing:
    """KEKs by id. The last one is active for new encryptions; older ones only decrypt."""

    keks: dict[str, bytes]
    active_id: str
    blind_index_key: bytes

    @classmethod
    def parse(cls, keks_spec: str, blind_index_key_b64: str) -> "KeyRing":
        # Format: "v1:<base64>,v2:<base64>" - append a new version to rotate.
        keks: dict[str, bytes] = {}
        for part in filter(None, (p.strip() for p in keks_spec.split(","))):
            key_id, _, encoded = part.partition(":")
            key = base64.b64decode(encoded)
            if len(key) != 32 or not key_id:
                raise CryptoConfigError("each KEK must be '<id>:<base64 of 32 bytes>'")
            keks[key_id] = key
        if not keks:
            raise CryptoConfigError("no KEK configured")
        blind = base64.b64decode(blind_index_key_b64)
        if len(blind) < 32:
            raise CryptoConfigError("blind index key must be at least 32 bytes")
        return cls(keks=keks, active_id=list(keks)[-1], blind_index_key=blind)


@lru_cache
def get_key_ring() -> KeyRing:
    settings = get_settings()
    if not settings.keks or not settings.blind_index_key:
        raise CryptoConfigError(
            "CARESLOT_KEKS and CARESLOT_BLIND_INDEX_KEY must be set "
            "(locally `make up` generates them into .env)"
        )
    return KeyRing.parse(
        settings.keks.get_secret_value(), settings.blind_index_key.get_secret_value()
    )


def encrypt(plaintext: str, aad: str, ring: KeyRing | None = None) -> bytes:
    ring = ring or get_key_ring()
    dek = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(_NONCE_BYTES)
    ciphertext = AESGCM(dek).encrypt(nonce, plaintext.encode(), aad.encode())

    kek_id = ring.active_id.encode()
    wrap_nonce = os.urandom(_NONCE_BYTES)
    wrapped_dek = AESGCM(ring.keks[ring.active_id]).encrypt(wrap_nonce, dek, kek_id)

    # version | len(kek_id) | kek_id | wrap_nonce | len(wrapped_dek) | wrapped_dek | nonce | ct
    return (
        struct.pack(">BB", _FORMAT_VERSION, len(kek_id))
        + kek_id
        + wrap_nonce
        + struct.pack(">H", len(wrapped_dek))
        + wrapped_dek
        + nonce
        + ciphertext
    )


def decrypt(blob: bytes, aad: str, ring: KeyRing | None = None) -> str:
    ring = ring or get_key_ring()
    version, id_len = struct.unpack_from(">BB", blob, 0)
    if version != _FORMAT_VERSION:
        raise ValueError(f"unsupported ciphertext version {version}")
    pos = 2
    kek_id = blob[pos : pos + id_len]
    pos += id_len
    wrap_nonce = blob[pos : pos + _NONCE_BYTES]
    pos += _NONCE_BYTES
    (wrapped_len,) = struct.unpack_from(">H", blob, pos)
    pos += 2
    wrapped_dek = blob[pos : pos + wrapped_len]
    pos += wrapped_len
    nonce = blob[pos : pos + _NONCE_BYTES]
    ciphertext = blob[pos + _NONCE_BYTES :]

    kek = ring.keks.get(kek_id.decode())
    if kek is None:
        raise ValueError("ciphertext was wrapped with an unknown KEK")
    dek = AESGCM(kek).decrypt(wrap_nonce, wrapped_dek, kek_id)
    return AESGCM(dek).decrypt(nonce, ciphertext, aad.encode()).decode()


def kek_id_of(blob: bytes) -> str:
    """Which KEK wrapped this value - used by the key-rotation job to find stale rows."""
    _, id_len = struct.unpack_from(">BB", blob, 0)
    return blob[2 : 2 + id_len].decode()


def blind_index(value: str, ring: KeyRing | None = None) -> str:
    ring = ring or get_key_ring()
    normalised = value.strip().upper().encode()
    return hmac.new(ring.blind_index_key, normalised, hashlib.sha256).hexdigest()
