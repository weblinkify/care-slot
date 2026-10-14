"""Consent use cases. Only the patient decides about their own consent; all access audited."""

from collections.abc import Callable
from typing import Protocol
from uuid import UUID

from careslot.modules.consent.domain.events import ConsentGranted, ConsentWithdrawn
from careslot.modules.consent.domain.model import (
    ConsentDecision,
    ConsentPurpose,
    ConsentState,
    current_state,
)
from careslot.shared.audit import AccessReason, AuditRecord, AuditSink
from careslot.shared.clock import Clock
from careslot.shared.errors import ForbiddenError
from careslot.shared.events import DomainEvent
from careslot.shared.principal import Principal, Role


class ConsentRepository(Protocol):
    def history(self, patient_id: UUID) -> list[ConsentDecision]: ...
    def add(self, decision: ConsentDecision) -> None: ...
    def delete_for_patient(self, patient_id: UUID) -> int: ...


class ConsentService:
    def __init__(
        self,
        repo: ConsentRepository,
        audit: AuditSink,
        publish: Callable[[DomainEvent], None],
        clock: Clock,
    ) -> None:
        self._repo = repo
        self._audit = audit
        self._publish = publish
        self._clock = clock

    def overview(self, principal: Principal) -> tuple[list[ConsentState], list[ConsentDecision]]:
        patient_id = self._own(principal)
        history = self._repo.history(patient_id)
        self._record(principal, "consent.read", patient_id)
        return current_state(history), sorted(history, key=lambda d: d.decided_at, reverse=True)

    def decide(self, principal: Principal, purpose: ConsentPurpose, granted: bool) -> ConsentState:
        patient_id = self._own(principal)
        states = {s.purpose: s for s in current_state(self._repo.history(patient_id))}
        if states[purpose].granted == granted and states[purpose].decided_at is not None:
            return states[purpose]  # idempotent: repeating a decision records nothing new

        decision = ConsentDecision.new(patient_id, purpose, granted, self._clock())
        self._repo.add(decision)
        self._record(principal, "consent.grant" if granted else "consent.withdraw", patient_id)
        event_type = ConsentGranted if granted else ConsentWithdrawn
        self._publish(event_type(patient_id=patient_id, purpose=purpose))
        return ConsentState(purpose, granted, decision.decided_at, decision.policy_version)

    def _own(self, principal: Principal) -> UUID:
        # Consent is personal: no clinician or admin can decide on a patient's behalf here.
        if principal.role is not Role.PATIENT:
            raise ForbiddenError("Only the patient can view or change their consent.")
        return principal.subject

    def _record(self, principal: Principal, action: str, patient_id: UUID) -> None:
        self._audit(
            AuditRecord(
                actor=principal,
                action=action,
                resource_type="consent",
                resource_id=str(patient_id),
                patient_id=patient_id,
                reason=AccessReason.SELF_SERVICE,
            )
        )
