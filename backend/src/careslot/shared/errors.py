"""RFC 7807 problem-details error model.

Every error the API returns has the same shape, so clients (and the generated OpenAPI spec)
need exactly one error schema. Domain code raises `DomainError` subclasses that know nothing
about HTTP except a status hint; the mapping to a response lives here, at the edge.
"""

from collections.abc import Mapping
from typing import Any, ClassVar

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from careslot.shared.routes import route_index

PROBLEM_JSON = "application/problem+json"
PROBLEM_BASE = "https://careslot.example/problems/"


class Problem(BaseModel):
    """RFC 7807 problem details."""

    type: str
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    errors: list[dict[str, Any]] | None = None


class DomainError(Exception):
    """Base class for expected, client-caused errors."""

    status: ClassVar[int] = 400
    code: ClassVar[str] = "bad-request"
    title: ClassVar[str] = "Bad request"

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.title)
        self.detail = detail


class NotFoundError(DomainError):
    status = 404
    code = "not-found"
    title = "Resource not found"


class ConflictError(DomainError):
    status = 409
    code = "conflict"
    title = "Conflict with current state"


class BusinessRuleError(DomainError):
    status = 422
    code = "business-rule-violation"
    title = "Business rule violated"


class AuthenticationError(DomainError):
    status = 401
    code = "unauthenticated"
    title = "Authentication required"


class ForbiddenError(DomainError):
    """Raised for authorisation failures.

    Note: for resources owned by another patient we raise `NotFoundError` instead, so the API
    does not reveal that a record exists (prevents ID enumeration).
    """

    status = 403
    code = "forbidden"
    title = "Not allowed"


def _problem(
    status: int,
    code: str,
    title: str,
    request: Request,
    headers: Mapping[str, str] | None = None,
    **extra: Any,
) -> JSONResponse:
    body = Problem(
        type=PROBLEM_BASE + code, title=title, status=status, instance=request.url.path, **extra
    )
    return JSONResponse(
        body.model_dump(exclude_none=True),
        status_code=status,
        media_type=PROBLEM_JSON,
        headers=headers,
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(request: Request, exc: DomainError) -> JSONResponse:
        retry_after = getattr(exc, "retry_after", None)
        headers = {"Retry-After": str(retry_after)} if retry_after else None
        return _problem(exc.status, exc.code, exc.title, request, headers, detail=exc.detail)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Only expose location + message; never echo the submitted input back (could be PII).
        errors = [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]
        return _problem(
            422, "validation-error", "Request validation failed", request, errors=errors
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "not-found" if exc.status_code == 404 else f"http-{exc.status_code}"
        headers = dict(exc.headers or {})
        if exc.status_code == 405:
            # RFC 9110: `Allow` must list every supported method. The router only knows the
            # first route it matched, so take the documented methods of the path instead.
            found = route_index(app).match(request.url.path)
            if found:
                headers["Allow"] = ", ".join(found[1])
        return _problem(exc.status_code, code, str(exc.detail), request, headers)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Details go to logs/traces, never to the client.
        return _problem(500, "internal-error", "Internal server error", request)


def problem_openapi(app: FastAPI) -> None:
    """Make the published contract match what the API actually sends for errors.

    FastAPI documents error models under `application/json` and adds its own 422 schema;
    we send `application/problem+json` with `Problem` for every error. This post-processes
    the generated document once: every 4xx/5xx becomes problem+json, and every operation
    documents 400 (malformed body) and 422 (validation) - found by the contract tests.
    """
    generate = app.openapi

    def openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        spec = generate()
        problem_ref = {"$ref": "#/components/schemas/Problem"}
        components = spec.setdefault("components", {}).setdefault("schemas", {})
        components["Problem"] = Problem.model_json_schema()
        for path_item in spec.get("paths", {}).values():
            for operation in path_item.values():
                responses = operation.setdefault("responses", {})
                responses.setdefault("400", {"description": "Malformed request"})
                responses.setdefault("422", {"description": "Validation error"})
                for status, response in responses.items():
                    if status[0] in "45":
                        response["content"] = {PROBLEM_JSON: {"schema": problem_ref}}
        for unused in ("HTTPValidationError", "ValidationError"):
            components.pop(unused, None)
        app.openapi_schema = spec
        return spec

    app.openapi = openapi  # type: ignore[method-assign]


# Reusable OpenAPI response documentation for routers.
PROBLEM_RESPONSES: dict[int | str, dict[str, Any]] = {
    code: {"description": desc}  # content filled in by problem_openapi()
    for code, desc in {
        400: "Bad request",
        401: "Unauthenticated",
        403: "Forbidden",
        404: "Not found",
        409: "Conflict",
        422: "Validation error or business rule violated",
        429: "Too many requests",
    }.items()
}
