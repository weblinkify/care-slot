"""Load synthetic demo data: `make seed` (or `python -m careslot.seed`).

Everything here is invented. Names are obviously fictional and identity codes (added with the
patients module) use a reserved test range. Never add real people, real clinics or values
copied from production - see docs/ai-development-policy.md.

Idempotent: fixed UUIDs and "insert if missing", so running it twice is harmless.
"""

from datetime import UTC, date, datetime, time, timedelta
from uuid import NAMESPACE_URL, UUID, uuid5
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from careslot.modules.scheduling.infrastructure.models import ClinicianRow, ClinicRow, SlotRow
from careslot.shared.db import get_session_factory
from careslot.shared.logging import configure_logging, get_logger

# Stable IDs: the mock identity provider's demo users map onto these (see careslot.mock_idp).
CLINIC_ID = UUID("0b6f4c64-0000-4000-8000-000000000001")
CLINICIANS = {
    UUID("c1000000-0000-4000-8000-000000000001"): ("Dr. Aava Example", "General practice"),
    UUID("c1000000-0000-4000-8000-000000000002"): ("Dr. Onni Sample", "Physiotherapy"),
}
SLOT_MINUTES = 30
DAY_START, DAY_END = time(8, 0), time(16, 0)
DAYS_AHEAD = 14

log = get_logger(__name__)


def _seed_scheduling(session: Session, today: date) -> int:
    tz = ZoneInfo("Europe/Helsinki")
    if session.get(ClinicRow, CLINIC_ID) is None:
        session.add(ClinicRow(id=CLINIC_ID, name="Synthetic Health Centre", timezone=tz.key))
        session.flush()
    for cid, (name, specialty) in CLINICIANS.items():
        if session.get(ClinicianRow, cid) is None:
            session.add(
                ClinicianRow(id=cid, clinic_id=CLINIC_ID, display_name=name, specialty=specialty)
            )
    session.flush()

    existing = {
        (cid, ts) for cid, ts in session.execute(select(SlotRow.clinician_id, SlotRow.starts_at))
    }
    created = 0
    for offset in range(DAYS_AHEAD):
        day = today + timedelta(days=offset)
        if day.weekday() >= 5:  # clinics are closed at weekends
            continue
        start = datetime.combine(day, DAY_START, tzinfo=tz)
        end = datetime.combine(day, DAY_END, tzinfo=tz)
        for cid in CLINICIANS:
            t = start
            while t < end:
                key = (cid, t.astimezone(UTC))
                if key not in existing:
                    session.add(
                        SlotRow(
                            id=_slot_id(cid, t),
                            clinician_id=cid,
                            starts_at=t,
                            ends_at=t + timedelta(minutes=SLOT_MINUTES),
                        )
                    )
                    created += 1
                t += timedelta(minutes=SLOT_MINUTES)
    return created


def _slot_id(clinician_id: UUID, starts_at: datetime) -> UUID:
    # Deterministic so re-running the seed never creates duplicates.
    return uuid5(NAMESPACE_URL, f"careslot:slot:{clinician_id}:{starts_at.isoformat()}")


def main() -> None:
    configure_logging()
    with get_session_factory()() as session:
        slots = _seed_scheduling(session, datetime.now(UTC).date())
        session.commit()
    log.info("seed.completed", slots_created=slots)


if __name__ == "__main__":
    main()
