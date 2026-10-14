"""Patients domain events (public). IDs only."""

from dataclasses import dataclass
from uuid import UUID

from careslot.shared.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class PatientErased(DomainEvent):
    patient_id: UUID
