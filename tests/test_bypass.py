"""Verify the operator-facing bypass reason counters."""

import asyncio
from typing import Any, Callable

from booster import CachePolicy, RocketBooster
from booster.bypass import (CREDENTIALS, METHOD, POLICY, REQUEST_DIRECTIVE, RESPONSE_DIRECTIVE,
                             STORED)

HEADERS = [(b"host", b"bypass.test")]


def build_scope(method: str, path: str, headers: list[tuple[bytes, bytes]] | None = None) -> dict[str, Any]:
    """Build a minimal HTTP scope for the engine."""
    return {"type": "http", "method": method, "path": path,
            "headers": list(headers or HEADERS)}


async def call(engine: RocketBooster, scope: dict[str, Any]) -> bytes:
    """Drive one request through the engine and return the response body."""
    chunks: list[bytes] = []

    async def receive() -> dict[str, Any]:
        """Provide the empty request body."""
        return {"type": "http.request", "body": b""}

    async def send(message: dict[str, Any]) -> None:
        """Collect the response body."""
        if message["type"] == "http.response.body":
            chunks.append(message.get("body", b""))

    await engine(scope, receive, send)
    return b"".join(chunks)


def origin(control: str = "public", body: bytes = b"body") -> Callable:
    """Create an origin that declares the given cache control."""
    async def application(scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        """Send one response with the requested cache control."""
        headers = [(b"content-type", b"text/plain"), (b"cache-control", control.encode())]
        await send({"type": "http.response.start", "status": 200, "headers": headers})
        await send({"type": "http.response.body", "body": body})
    return application


def reasons(engine: RocketBooster) -> dict[str, int]:
    """Read the bypass counters from the status snapshot."""
    return engine.get_status()["metrics"]["bypass_reasons"]


def test_public_response_is_counted_as_stored() -> None:
    """A stored response must be counted."""
    engine = RocketBooster(origin())
    asyncio.run(call(engine, build_scope("GET", "/public")))
    assert reasons(engine).get(STORED) == 1


def test_credentialed_request_is_counted() -> None:
    """A cookie-bearing request must be counted as credentialed."""
    engine = RocketBooster(origin())
    headers = HEADERS + [(b"cookie", b"session=secret")]
    asyncio.run(call(engine, build_scope("GET", "/public", headers)))
    assert reasons(engine).get(CREDENTIALS) == 1


def test_range_request_is_counted_as_a_request_directive() -> None:
    """A range request must be counted."""
    engine = RocketBooster(origin())
    headers = HEADERS + [(b"range", b"bytes=0-10")]
    asyncio.run(call(engine, build_scope("GET", "/public", headers)))
    assert reasons(engine).get(REQUEST_DIRECTIVE) == 1


def test_private_response_is_counted() -> None:
    """A private response must be counted as not public."""
    engine = RocketBooster(origin("private, no-store"))
    asyncio.run(call(engine, build_scope("GET", "/public")))
    assert reasons(engine).get(RESPONSE_DIRECTIVE) == 1


def test_unselected_route_is_counted() -> None:
    """A route outside the policy must be counted."""
    engine = RocketBooster(origin(), cache_policy=CachePolicy(include_paths=("/public",)))
    asyncio.run(call(engine, build_scope("GET", "/private-page")))
    assert reasons(engine).get(POLICY) == 1


def test_write_method_is_counted() -> None:
    """A write must be counted as a method that is not read."""
    engine = RocketBooster(origin())
    asyncio.run(call(engine, build_scope("POST", "/public")))
    assert reasons(engine).get(METHOD) == 1


def test_snapshot_holds_no_request_data() -> None:
    """The snapshot must not leak cookies, tokens, paths or payloads."""
    engine = RocketBooster(origin())
    headers = HEADERS + [(b"cookie", b"session=secret-value")]
    asyncio.run(call(engine, build_scope("GET", "/secret-path", headers)))
    snapshot = str(engine.get_status())
    assert "secret-value" not in snapshot
    assert "secret-path" not in snapshot
    assert "/public" not in snapshot
