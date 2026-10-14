"""Consent: provable, purpose-specific, withdrawable, patient-only."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from careslot.modules.consent.application.services import ConsentService
from careslot.modules.consent.domain.model import (
    CURRENT_POLICY_VERSION,
    ConsentDecision,
    ConsentPurpose,
    current_state,
)
from careslot.shared.errors import ForbiddenError
from careslot.shared.events import DomainEvent
from careslot.shared.principal import Principal, Role
from tests.fakes import RecordingAudit

T0 = datetime(2026, 3, 2, 8, 0, tzinfo=UTC)


class FakeConsentRepo:
    def __init__(self) -> None:
        self.rows: list[ConsentDecision] = []

    def history(self, patient_id: UUID) -> list[ConsentDecision]:
        return [d for d in self.rows if d.patient_id == patient_id]

    def add(self, decision: ConsentDecision) -> None:
        self.rows.append(decision)

    def delete_for_patient(self, patient_id: UUID) -> int:
        before = len(self.rows)
        self.rows = [d for d in self.rows if d.patient_id != patient_id]
        return before - len(self.rows)


class Clock:
    def __init__(self) -> None:
        self.now = T0

    def __call__(self) -> datetime:
        self.now += timedelta(seconds=1)
        return self.now


Ctx = tuple[ConsentService, FakeConsentRepo, RecordingAudit, list[DomainEvent]]


@pytest.fixture
def ctx() -> Ctx:
    repo, audit, events = FakeConsentRepo(), RecordingAudit(), []
    service = ConsentService(repo=repo, audit=audit, publish=events.append, clock=Clock())
    return service, repo, audit, events


def test_nothing_is_consented_by_default() -> None:
    assert all(not s.granted and s.decided_at is None for s in current_state([]))


def test_latest_decision_wins_per_purpose() -> None:
    p = uuid4()
    decisions = [
        ConsentDecision.new(p, ConsentPurpose.RESEARCH, True, T0),
        ConsentDecision.new(p, ConsentPurpose.RESEARCH, False, T0 + timedelta(days=1)),
        ConsentDecision.new(p, ConsentPurpose.AI_SUMMARIES, True, T0),
    ]
    state = {s.purpose: s.granted for s in current_state(decisions)}
    assert state == {
        ConsentPurpose.RESEARCH: False,
        ConsentPurpose.AI_SUMMARIES: True,
        ConsentPurpose.REGIONAL_RECORD_SHARING: False,
    }


def test_grant_then_withdraw_keeps_provable_history_and_emits_events(ctx: Ctx) -> None:
    service, repo, audit, events = ctx
    me = Principal(uuid4(), Role.PATIENT)

    service.decide(me, ConsentPurpose.RESEARCH, True)
    service.decide(me, ConsentPurpose.RESEARCH, False)

    assert [d.granted for d in repo.rows] == [True, False]  # nothing overwritten
    assert {d.policy_version for d in repo.rows} == {CURRENT_POLICY_VERSION}
    assert [e.name for e in events] == ["ConsentGranted", "ConsentWithdrawn"]
    assert audit.actions == ["consent.grant", "consent.withdraw"]


def test_repeating_the_same_decision_is_idempotent(ctx: Ctx) -> None:
    service, repo, _audit, events = ctx
    me = Principal(uuid4(), Role.PATIENT)
    service.decide(me, ConsentPurpose.AI_SUMMARIES, True)
    service.decide(me, ConsentPurpose.AI_SUMMARIES, True)
    assert len(repo.rows) == 1 and len(events) == 1


@pytest.mark.parametrize("role", [Role.CLINICIAN, Role.ADMIN])
def test_nobody_else_can_decide_for_a_patient(ctx: Ctx, role: Role) -> None:
    service, *_ = ctx
    with pytest.raises(ForbiddenError):
        service.decide(Principal(uuid4(), role), ConsentPurpose.RESEARCH, True)
