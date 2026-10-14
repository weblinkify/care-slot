"""Liveness and readiness probes.

/health  - is the process alive? Never touches dependencies, so a slow database does not get
           healthy pods killed by the orchestrator (a classic cascading-failure cause).
/ready   - can this instance serve traffic right now? Checks the database; when it fails the
           load balancer stops routing here but the process is not restarted.
"""

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from careslot.shared.db import get_engine, ping

router = APIRouter(tags=["operations"])


class HealthStatus(BaseModel):
    status: str
    checks: dict[str, str] = {}


@router.get("/health", response_model=HealthStatus)
def health() -> HealthStatus:
    return HealthStatus(status="ok")


@router.get(
    "/ready",
    response_model=HealthStatus,
    responses={503: {"model": HealthStatus, "description": "Not ready"}},
)
def ready(response: Response) -> HealthStatus:
    db_ok = ping(get_engine())
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthStatus(
        status="ok" if db_ok else "unavailable", checks={"database": "ok" if db_ok else "down"}
    )
