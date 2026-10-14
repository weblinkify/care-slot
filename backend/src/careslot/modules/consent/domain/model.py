"""Consent domain.

Consent is modelled as an append-only history of decisions, not a mutable boolean:
GDPR art. 7(1) requires the controller to *demonstrate* that consent was given - when, for
what purpose, and under which version of the privacy notice. The current state of a purpose
is simply the latest decision. Withdrawing is exactly as easy as granting (art. 7(3)).
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

# Bump when the privacy notice text for any purpose changes; decisions record the version
# the patient actually saw.
CURRENT_POLICY_VERSION = "2026-01"


class ConsentPurpose(StrEnum):
    # Share appointment history with the regional health record so other providers see it.
    REGIONAL_RECORD_SHARING = "regional-record-sharing"
    # Include pseudonymised appointment data in research data extracts.
    RESEARCH = "research"
    # Include the patient's appointments in AI-generated daily summaries for clinicians.
    AI_SUMMARIES = "ai-summaries"


# Opt-in by default for everything: no decision recorded means no consent.
DEFAULT_GRANTED = False


@dataclass(frozen=True)
class ConsentDecision:
    id: UUID
    patient_id: UUID
    purpose: ConsentPurpose
    granted: bool
    decided_at: datetime
    policy_version: str

    @classmethod
    def new(
        cls, patient_id: UUID, purpose: ConsentPurpose, granted: bool, now: datetime
    ) -> "ConsentDecision":
        return cls(
            id=uuid4(),
            patient_id=patient_id,
            purpose=purpose,
            granted=granted,
            decided_at=now,
            policy_version=CURRENT_POLICY_VERSION,
        )


@dataclass(frozen=True)
class ConsentState:
    purpose: ConsentPurpose
    granted: bool
    decided_at: datetime | None  # None: never decided (default applies)
    policy_version: str | None


def current_state(decisions: list[ConsentDecision]) -> list[ConsentState]:
    """Latest decision per purpose; every purpose appears, defaulting to not granted."""
    latest: dict[ConsentPurpose, ConsentDecision] = {}
    for d in sorted(decisions, key=lambda d: d.decided_at):
        latest[d.purpose] = d
    return [
        ConsentState(
            purpose=p,
            granted=latest[p].granted if p in latest else DEFAULT_GRANTED,
            decided_at=latest[p].decided_at if p in latest else None,
            policy_version=latest[p].policy_version if p in latest else None,
        )
        for p in ConsentPurpose
    ]
