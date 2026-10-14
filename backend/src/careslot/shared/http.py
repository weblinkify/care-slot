"""HTTP hardening applied to every response."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

API_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    # The API serves JSON only, so the strictest possible policy applies.
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    # Responses can contain patient data: never let browsers or proxies cache them.
    "Cache-Control": "no-store",
}

# Swagger UI loads its JS/CSS from a CDN, so the interactive docs get a relaxed CSP.
DOCS_CSP = (
    "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: "
    "https://fastapi.tiangolo.com; frame-ancestors 'none'"
)


def install_security_headers(app: FastAPI, docs_path: str) -> None:
    @app.middleware("http")
    async def _headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        for name, value in API_HEADERS.items():
            response.headers.setdefault(name, value)
        if request.url.path.startswith(docs_path):
            response.headers["Content-Security-Policy"] = DOCS_CSP
        return response
