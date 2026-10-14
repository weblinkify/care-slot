"""Consent bounded context: purpose-specific, versioned, provable consent decisions.

PUBLIC INTERFACE: events, the purpose enum, a consent query for other modules, and the
reaction to patient erasure.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from careslot.modules.consent.domain.events import ConsentGranted, ConsentWithdrawn
from careslot.modules.consent.domain.model import ConsentPurpose
from careslot.modules.consent.infrastructure.repository import SqlConsentRepository, has_consent
from careslot.modules.patients import PatientErased


def on_patient_erased(event: PatientErased, session: Session) -> None:
    """After erasure no processing happens, so proof of consent is no longer needed."""
    SqlConsentRepository(session).delete_for_patient(event.patient_id)


def patient_has_consent(session: Session, patient_id: UUID, purpose: ConsentPurpose) -> bool:
    return has_consent(session, patient_id, purpose)


__all__ = [
    "ConsentGranted",
    "ConsentPurpose",
    "ConsentWithdrawn",
    "on_patient_erased",
    "patient_has_consent",
]
