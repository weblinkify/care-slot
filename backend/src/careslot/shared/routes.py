"""Index of the documented API paths, built from the public OpenAPI document.

Used where we need to reason about "which documented route is this request?" without
depending on framework internals: the access log (route template) and 405 responses
(the RFC 9110 `Allow` header lists every documented method of the path).
"""

import re
from functools import cached_property
from typing import Any

from fastapi import FastAPI

_HTTP_METHODS = {"get", "put", "post", "delete", "patch", "head", "options"}


class RouteIndex:
    def __init__(self, app: FastAPI) -> None:
        self._app = app

    @cached_property
    def _templates(self) -> list[tuple[re.Pattern[str], str, list[str]]]:
        paths: dict[str, dict[str, Any]] = self._app.openapi()["paths"]
        # Static templates first, so /patients/me wins over /patients/{patient_id}.
        ordered = sorted(paths, key=lambda t: (t.count("{"), t))
        return [
            (
                re.compile("^" + re.sub(r"\\{[^/]+?\\}", "[^/]+", re.escape(t)) + "$"),
                t,
                sorted(m.upper() for m in paths[t] if m in _HTTP_METHODS),
            )
            for t in ordered
        ]

    def match(self, path: str) -> tuple[str, list[str]] | None:
        for pattern, template, methods in self._templates:
            if pattern.match(path):
                return template, methods
        return None

    def template_for(self, path: str) -> str:
        found = self.match(path)
        return found[0] if found else "unmatched"


def route_index(app: FastAPI) -> RouteIndex:
    index: RouteIndex | None = getattr(app.state, "route_index", None)
    if index is None:
        index = RouteIndex(app)
        app.state.route_index = index
    return index
