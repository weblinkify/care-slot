from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from careslot.modules.consent.domain.model import ConsentDecision, ConsentPurpose
from careslot.modules.consent.infrastructure.models import ConsentDecisionRow


class SqlConsentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def history(self, patient_id: UUID) -> list[ConsentDecision]:
        rows = self._session.scalars(
            select(ConsentDecisionRow)
            .where(ConsentDecisionRow.patient_id == patient_id)
            .order_by(ConsentDecisionRow.decided_at)
        )
        return [
            ConsentDecision(
                id=r.id,
                patient_id=r.patient_id,
                purpose=ConsentPurpose(r.purpose),
                granted=r.granted,
                decided_at=r.decided_at,
                policy_version=r.policy_version,
            )
            for r in rows
        ]

    def add(self, decision: ConsentDecision) -> None:
        self._session.add(
            ConsentDecisionRow(
                id=decision.id,
                patient_id=decision.patient_id,
                purpose=decision.purpose.value,
                granted=decision.granted,
                decided_at=decision.decided_at,
                policy_version=decision.policy_version,
            )
        )
        self._session.flush()

    def delete_for_patient(self, patient_id: UUID) -> int:
        result = self._session.execute(
            delete(ConsentDecisionRow).where(ConsentDecisionRow.patient_id == patient_id)
        )
        return int(result.rowcount)  # type: ignore[attr-defined]


def has_consent(session: Session, patient_id: UUID, purpose: ConsentPurpose) -> bool:
    latest = session.scalar(
        select(ConsentDecisionRow.granted)
        .where(ConsentDecisionRow.patient_id == patient_id, ConsentDecisionRow.purpose == purpose)
        .order_by(ConsentDecisionRow.decided_at.desc())
        .limit(1)
    )
    return bool(latest)
