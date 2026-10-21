"""Verify the opt-in Vary allow list for hosting layers that add their own field."""

from typing import Any

from booster import RocketBooster
from booster.http_policy import response_cacheable

HEADERS = [(b"host", b"vary.test")]


def build_scope(path: str, headers: list[tuple[bytes, bytes]] | None = None) -> dict[str, Any]:
    """Build a minimal HTTP scope for the engine."""
    return {"type": "http", "method": "GET", "path": path, "headers": list(headers or HEADERS)}


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


def origin(vary: str) -> Any:
    """Create an origin that declares the given Vary header."""
    async def application(scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Send one public asset response."""
        headers = [(b"content-type", b"text/css"), (b"cache-control", b"public, max-age=300"),
                   (b"vary", vary.encode())]
        await send({"type": "http.response.start", "status": 200, "headers": headers})
        await send({"type": "http.response.body", "body": b"body{}"})
    return application


def test_default_policy_refuses_an_extra_vary_field() -> None:
    """Without the allow list an extra Vary field blocks the cache."""
    headers = {"cache-control": "public, max-age=300", "vary": "Accept-Encoding, User-Agent"}
    assert response_cacheable(headers, is_static=True) is False


def test_allowed_vary_field_admits_the_response() -> None:
    """The allow list admits exactly the field the host declared."""
    headers = {"cache-control": "public, max-age=300", "vary": "Accept-Encoding, User-Agent"}
    assert response_cacheable(headers, is_static=True, allowed_vary=("user-agent",)) is True
    assert response_cacheable(headers, is_static=True, allowed_vary=("cookie",)) is False


def test_engine_stores_the_asset_only_with_the_allow_list() -> None:
    """The engine must store the asset only when the host allows the field."""
    blocked = RocketBooster(origin("Accept-Encoding, User-Agent"))
    assert blocked.cache.count() == 0

    allowed = RocketBooster(origin("Accept-Encoding, User-Agent"), allowed_vary=("User-Agent",))
    import asyncio

    asyncio.run(call(allowed, build_scope("/static/app.css")))
    assert allowed.cache.count() == 1
    assert allowed.get_status()["configuration"]["allowed_vary"] == ["user-agent"]
