"""Consent domain events (public). IDs and purpose only."""

from dataclasses import dataclass
from uuid import UUID

from careslot.modules.consent.domain.model import ConsentPurpose
from careslot.shared.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class ConsentGranted(DomainEvent):
    patient_id: UUID
    purpose: ConsentPurpose


@dataclass(frozen=True, kw_only=True)
class ConsentWithdrawn(DomainEvent):
    patient_id: UUID
    purpose: ConsentPurpose
