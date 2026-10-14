"""Hash chain: any edit, deletion or reordering of history is detected."""

import dataclasses
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from careslot.modules.audit.domain.model import (
    GENESIS_HASH,
    AuditEntry,
    compute_hash,
    verify_chain,
)

T0 = datetime(2026, 3, 2, 8, 0, tzinfo=UTC)


def build_chain(n: int) -> list[AuditEntry]:
    chain: list[AuditEntry] = []
    prev = GENESIS_HASH
    for i in range(n):
        draft = AuditEntry(
            id=i + 1,
            occurred_at=T0 + timedelta(seconds=i),
            actor_id=uuid4(),
            actor_role="patient",
            action="appointment.read",
            resource_type="appointment",
            resource_id=str(uuid4()),
            patient_id=uuid4(),
            reason="self-service",
            prev_hash=prev,
            hash="",
        )
        entry = dataclasses.replace(draft, hash=compute_hash(prev, draft))
        chain.append(entry)
        prev = entry.hash
    return chain


def test_intact_chain_verifies() -> None:
    result = verify_chain(build_chain(5))
    assert (result.valid, result.entries_checked) == (True, 5)


def test_edited_entry_is_detected() -> None:
    chain = build_chain(5)
    chain[2] = dataclasses.replace(chain[2], action="appointment.cancel")  # rewrite history
    result = verify_chain(chain)
    assert (result.valid, result.first_invalid_id) == (False, 3)


def test_deleted_entry_is_detected() -> None:
    chain = build_chain(5)
    del chain[1]
    assert verify_chain(chain).first_invalid_id == 3


def test_recomputed_hash_after_edit_still_breaks_the_next_link() -> None:
    # An attacker who edits an entry AND recomputes its hash still breaks entry n+1.
    chain = build_chain(5)
    edited = dataclasses.replace(chain[2], reason="treatment")
    chain[2] = dataclasses.replace(edited, hash=compute_hash(edited.prev_hash, edited))
    assert verify_chain(chain).first_invalid_id == 4
