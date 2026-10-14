"""Audit log domain: entries and the hash chain that makes tampering evident.

Each entry stores `hash = SHA-256(prev_hash + canonical JSON of the entry)`. Changing,
deleting or reordering any historical entry breaks every hash after it, which `verify_chain`
detects. The database additionally *prevents* modification (append-only trigger), so the
chain is the second line of defence: it also catches tampering by someone with enough
database privileges to disable the trigger. (ADR-0004)
"""

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class AuditEntry:
    id: int | None  # assigned by the database
    occurred_at: datetime
    actor_id: UUID | None
    actor_role: str | None
    action: str
    resource_type: str
    resource_id: str
    patient_id: UUID | None
    reason: str
    prev_hash: str
    hash: str

    def canonical(self) -> bytes:
        """Deterministic serialisation of everything the hash protects."""
        payload = {
            "occurred_at": self.occurred_at.isoformat(),
            "actor_id": str(self.actor_id) if self.actor_id else None,
            "actor_role": self.actor_role,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "patient_id": str(self.patient_id) if self.patient_id else None,
            "reason": self.reason,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def compute_hash(prev_hash: str, entry: AuditEntry) -> str:
    return hashlib.sha256(prev_hash.encode() + entry.canonical()).hexdigest()


@dataclass(frozen=True)
class ChainVerification:
    valid: bool
    entries_checked: int
    first_invalid_id: int | None = None


def verify_chain(entries: Iterable[AuditEntry]) -> ChainVerification:
    expected_prev = GENESIS_HASH
    checked = 0
    for entry in entries:
        if entry.prev_hash != expected_prev or compute_hash(entry.prev_hash, entry) != entry.hash:
            return ChainVerification(
                valid=False, entries_checked=checked, first_invalid_id=entry.id
            )
        expected_prev = entry.hash
        checked += 1
    return ChainVerification(valid=True, entries_checked=checked)
