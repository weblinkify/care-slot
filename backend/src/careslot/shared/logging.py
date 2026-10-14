"""Structured JSON logging with a personal-data redaction safety net.

The primary rule (AGENTS.md) is: never log personal data. This processor is the second line
of defence - if someone accidentally logs a field with a sensitive name, the value is
replaced before it leaves the process. It is deliberately key-based rather than
content-based: pattern-matching values (e.g. regex for identity codes) is slow and gives a
false sense of safety.
"""

import logging
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog
from opentelemetry import trace

SENSITIVE_KEYS = frozenset(
    {
        "personal_identity_code",
        "pic",
        "ssn",
        "name",
        "full_name",
        "first_name",
        "last_name",
        "email",
        "phone",
        "address",
        "date_of_birth",
        "password",
        "token",
        "authorization",
    }
)
REDACTED = "[REDACTED]"


def redact_sensitive(
    _logger: Any, _method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    for key in list(event_dict.keys()):
        if key.lower() in SENSITIVE_KEYS:
            event_dict[key] = REDACTED
    return event_dict


def add_trace_context(
    _logger: Any, _method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Attach the active OpenTelemetry trace/span id: every log line links to its trace."""
    ctx = trace.get_current_span().get_span_context()
    if ctx.is_valid:
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            add_trace_context,
            redact_sensitive,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping()[level.upper()]
        ),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[no-any-return]
