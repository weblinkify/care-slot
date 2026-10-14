"""Retention job: `python -m careslot.jobs.retention` (run daily by the platform scheduler,
e.g. a Kubernetes CronJob or cloud scheduler - see infra/terraform).

Idempotent and safe to re-run: it deletes only what is past retention at the moment it runs,
and records what it did in the audit log (as a system actor).
"""

from datetime import timedelta

from careslot.modules.scheduling import system_service
from careslot.shared.config import get_settings
from careslot.shared.db import get_session_factory
from careslot.shared.logging import configure_logging, get_logger

log = get_logger(__name__)


def run() -> tuple[int, int]:
    retention = timedelta(days=get_settings().retention_appointment_days)
    with get_session_factory()() as session:
        appointments, slots = system_service(session).purge_expired(retention)
        session.commit()
    log.info("retention.completed", appointments_deleted=appointments, slots_deleted=slots)
    return appointments, slots


if __name__ == "__main__":
    configure_logging()
    run()
