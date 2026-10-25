"""Minimal host application used to prove the plugin recipe inside this repository."""

import asyncio
from typing import Any, Callable

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

import booster

ORIGIN_CALLS: dict[str, int] = {"total": 0}
CATALOG: dict[str, str] = {"value": "v1"}
ASSET = b"body{color:red}"


async def asset(request: Any) -> PlainTextResponse:
    """Serve a public, versioned asset."""
    ORIGIN_CALLS["total"] += 1
    return PlainTextResponse(ASSET, headers={"Cache-Control": "public, max-age=60"})


async def account(request: Any) -> PlainTextResponse:
    """Serve a personalized page that must never enter the shared cache."""
    ORIGIN_CALLS["total"] += 1
    return PlainTextResponse("user:abc", headers={"Cache-Control": "private, no-store"})


async def catalog(request: Any) -> PlainTextResponse:
    """Read shared state and change it on a write."""
    ORIGIN_CALLS["total"] += 1
    if request.method == "POST":
        CATALOG["value"] = "v2"
    return PlainTextResponse(CATALOG["value"], headers={"Cache-Control": "public, max-age=60"})


def build_app() -> Starlette:
    """Create the unaccelerated origin application."""
    return Starlette(routes=[Route("/static/app.v1.css", asset), Route("/account", account),
                             Route("/catalog", catalog, methods=["GET", "POST"])])


origin_app = build_app()
app = build_app()

engine = booster.attach(
    app,
    cache_policy=booster.CachePolicy(
        include_paths=("/static/",),
        exclude_paths=("/account/", "/catalog/"),
    ),
    enable_compression=False,
    enable_minification=False,
    max_cache_bytes=8 * 1024 * 1024,
    cache_ttl=600,
)


class SecurityHeaders:
    """Outer middleware that must decorate every response, including a cache hit."""

    def __init__(self, wrapped: Any) -> None:
        """Keep the wrapped application."""
        self.wrapped = wrapped

    async def __call__(self, scope: Any, receive: Callable, send: Callable) -> None:
        """Add a security header to every HTTP response."""
        async def send_with_headers(message: dict[str, Any]) -> None:
            """Attach the security header to the response start message."""
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-frame-options", b"DENY"))
                message = {**message, "headers": headers}
            await send(message)

        await self.wrapped(scope, receive, send_with_headers)


app.add_middleware(SecurityHeaders)


async def call(application: Any, method: str, path: str,
               headers: dict[str, str] | None = None) -> tuple[int, bytes, list[tuple[bytes, bytes]]]:
    """Drive one ASGI request and collect status, body and headers."""
    raw = [(b"host", b"example.test")]
    for name, value in (headers or {}).items():
        raw.append((name.lower().encode("ascii"), value.encode("ascii")))
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
             "method": method, "scheme": "http", "path": path,
             "raw_path": path.encode("utf-8"), "query_string": b"",
             "headers": raw, "client": ("127.0.0.1", 50000), "server": ("example.test", 80)}
    body = bytearray()
    status = 0
    response_headers: list[tuple[bytes, bytes]] = []

    async def receive() -> dict[str, Any]:
        """Provide an empty request body."""
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        """Collect the response messages."""
        nonlocal status
        if message["type"] == "http.response.start":
            status = message["status"]
            response_headers.extend(message.get("headers", []))
        elif message["type"] == "http.response.body":
            body.extend(message.get("body", b""))

    await application(scope, receive, send)
    return status, bytes(body), response_headers


def request(method: str, path: str, headers: dict[str, str] | None = None,
            application: Any = None) -> tuple[int, bytes, list[tuple[bytes, bytes]]]:
    """Send one request to the given application."""
    return asyncio.run(call(application or app, method, path, headers))
