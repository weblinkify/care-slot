"""Envelope encryption and blind index. Keys here are generated per test run."""

import base64
import os

import pytest
from cryptography.exceptions import InvalidTag

from careslot.shared.crypto import (
    CryptoConfigError,
    KeyRing,
    blind_index,
    decrypt,
    encrypt,
    kek_id_of,
)


def key() -> str:
    return base64.b64encode(os.urandom(32)).decode()


@pytest.fixture
def ring() -> KeyRing:
    return KeyRing.parse(f"v1:{key()}", key())


def test_round_trip(ring: KeyRing) -> None:
    blob = encrypt("010190-900R", "pat:1", ring)
    assert decrypt(blob, "pat:1", ring) == "010190-900R"
    assert b"010190" not in blob  # nothing readable at rest


def test_same_value_encrypts_differently_each_time(ring: KeyRing) -> None:
    # Fresh DEK + nonce per value: equal plaintexts are not linkable by ciphertext.
    assert encrypt("x", "a", ring) != encrypt("x", "a", ring)


def test_ciphertext_moved_to_another_row_fails(ring: KeyRing) -> None:
    blob = encrypt("010190-900R", "pat_patients.identity_code:row-1", ring)
    with pytest.raises(InvalidTag):
        decrypt(blob, "pat_patients.identity_code:row-2", ring)


def test_tampered_ciphertext_fails(ring: KeyRing) -> None:
    blob = bytearray(encrypt("secret", "a", ring))
    blob[-1] ^= 0x01
    with pytest.raises(InvalidTag):
        decrypt(bytes(blob), "a", ring)


def test_rotation_new_values_use_new_kek_old_values_still_decrypt() -> None:
    v1, blind = key(), key()
    old_ring = KeyRing.parse(f"v1:{v1}", blind)
    old_blob = encrypt("old", "a", old_ring)

    rotated = KeyRing.parse(f"v1:{v1},v2:{key()}", blind)
    new_blob = encrypt("new", "a", rotated)

    assert (kek_id_of(old_blob), kek_id_of(new_blob)) == ("v1", "v2")
    assert decrypt(old_blob, "a", rotated) == "old"


def test_retired_kek_cannot_decrypt(ring: KeyRing) -> None:
    blob = encrypt("x", "a", ring)
    with pytest.raises(ValueError, match="unknown KEK"):
        decrypt(blob, "a", KeyRing.parse(f"v9:{key()}", key()))


def test_blind_index_is_stable_normalised_and_keyed(ring: KeyRing) -> None:
    assert blind_index("010190-900r ", ring) == blind_index("010190-900R", ring)
    other = KeyRing.parse(f"v1:{key()}", key())
    assert blind_index("010190-900R", ring) != blind_index("010190-900R", other)


@pytest.mark.parametrize("spec", ["", "v1:" + base64.b64encode(b"short").decode(), "nokey"])
def test_bad_key_config_fails_fast(spec: str) -> None:
    with pytest.raises((CryptoConfigError, ValueError)):
        KeyRing.parse(spec, key())
