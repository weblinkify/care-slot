"""Tracing and request logging.

- OpenTelemetry traces every request and every SQL statement. Spans are exported over OTLP
  when CARESLOT_OTEL_EXPORTER_ENDPOINT is set (Jaeger locally via
  `docker compose --profile observability up`; any OTLP backend in the cloud).
- Every log line carries the current trace_id, so a log line leads straight to its trace.
- One structured access-log line per request: method, *route template* (not the raw path),
  status and duration. Route templates aggregate well and avoid putting IDs from URLs into
  log analytics. Query strings and bodies are never logged (they may contain personal data).

SQL spans contain the parameterised statement only, never bound parameter values.
"""

import time
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode
from sqlalchemy import Engine, event

from careslot.shared.config import Settings
from careslot.shared.logging import get_logger
from careslot.shared.routes import route_index

log = get_logger("careslot.access")
_provider_installed = False


def setup_tracing(app: FastAPI, settings: Settings, engine: Engine | None = None) -> None:
    global _provider_installed
    if not _provider_installed:  # a process has exactly one global provider
        provider = TracerProvider(
            resource=Resource.create(
                {"service.name": "careslot-api", "deployment.environment": settings.environment}
            )
        )
        if settings.otel_exporter_endpoint:
            provider.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(endpoint=f"{settings.otel_exporter_endpoint}/v1/traces")
                )
            )
        trace.set_tracer_provider(provider)
        _provider_installed = True
    # Probes are high-volume and uninteresting; keep them out of traces.
    FastAPIInstrumentor.instrument_app(app, excluded_urls="health,ready")
    if engine is not None and not getattr(engine, "_careslot_instrumented", False):
        _instrument_engine(engine)
        engine._careslot_instrumented = True  # type: ignore[attr-defined]


def _instrument_engine(engine: Engine) -> None:
    """One span per SQL statement via SQLAlchemy's cursor events.

    Hand-rolled because opentelemetry-instrumentation-sqlalchemy does not support
    SQLAlchemy 2.1 yet; swap back when it does. Only the parameterised statement is recorded,
    never the bound values (which can contain personal data)."""
    tracer = trace.get_tracer("careslot.db")

    @event.listens_for(engine, "before_cursor_execute")
    def _start(conn: Any, cursor: Any, statement: str, *_args: Any) -> None:
        span = tracer.start_span(
            statement.split(None, 1)[0].upper() if statement else "SQL",
            kind=trace.SpanKind.CLIENT,
            attributes={"db.system": "postgresql", "db.statement": statement},
        )
        conn.info.setdefault("careslot_spans", []).append(span)

    @event.listens_for(engine, "after_cursor_execute")
    def _end(conn: Any, *_args: Any) -> None:
        spans = conn.info.get("careslot_spans")
        if spans:
            spans.pop().end()

    @event.listens_for(engine, "handle_error")
    def _error(context: Any) -> None:
        spans = context.connection.info.get("careslot_spans") if context.connection else None
        if spans:
            span = spans.pop()
            span.set_status(Status(StatusCode.ERROR, type(context.original_exception).__name__))
            span.end()


def install_access_log(app: FastAPI) -> None:
    @app.middleware("http")
    async def _access_log(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        if request.url.path not in ("/health", "/ready"):
            log.info(
                "http.request",
                method=request.method,
                route=route_index(app).template_for(request.url.path),
                status=response.status_code,
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
            )
        return response
