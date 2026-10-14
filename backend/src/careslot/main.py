"""Application composition root.

This is the only place that knows about every module: it wires routers, event handlers and
middleware together. Modules never import each other's internals (enforced by import-linter).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from careslot.modules.scheduling.api.router import router as scheduling_router
from careslot.shared.config import Settings, get_settings
from careslot.shared.errors import register_error_handlers
from careslot.shared.health import router as health_router
from careslot.shared.logging import configure_logging

API_V1 = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="CareSlot API",
        version="1.0.0",
        description=(
            "Appointment booking and patient-consent service. "
            "Showcase project - synthetic data only."
        ),
        openapi_url=f"{API_V1}/openapi.json",
        docs_url=f"{API_V1}/docs",
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(scheduling_router, prefix=API_V1)
    return app


app = create_app()
