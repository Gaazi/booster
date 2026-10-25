"""Verify the origin age handling for responses that are already cached upstream."""

from typing import Any

from booster import RocketBooster
from booster.http_policy import response_age, response_cacheable, response_ttl

HEADERS = [(b"host", b"age.test")]


def build_scope(path: str) -> dict[str, Any]:
    """Build a minimal HTTP scope for the engine."""
    return {"type": "http", "method": "GET", "path": path, "headers": list(HEADERS)}


async def call(engine: RocketBooster, scope: dict[str, Any]) -> tuple[bytes, list[tuple[bytes, bytes]]]:
    """Drive one request through the engine and collect the body and headers."""
    chunks: list[bytes] = []
    headers: list[tuple[bytes, bytes]] = []

    async def receive() -> dict[str, Any]:
        """Provide the empty request body."""
        return {"type": "http.request", "body": b""}

    async def send(message: dict[str, Any]) -> None:
        """Collect the response body and headers."""
        if message["type"] == "http.response.start":
            headers.extend(message.get("headers", []))
        elif message["type"] == "http.response.body":
            chunks.append(message.get("body", b""))

    await engine(scope, receive, send)
    return b"".join(chunks), headers


def origin(age: str = "81", max_age: str = "31536000") -> Any:
    """Create an origin that already served the response from its own cache."""
    async def application(scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Send one aged public asset response."""
        headers = [(b"content-type", b"text/css"),
                   (b"cache-control", f"public, max-age={max_age}".encode()),
                   (b"age", age.encode())]
        await send({"type": "http.response.start", "status": 200, "headers": headers})
        await send({"type": "http.response.body", "body": b"body{}"})
    return application


def test_response_age_is_read() -> None:
    """The Age header must be read as seconds."""
    assert response_age({"age": "81"}) == 81.0
    assert response_age({}) == 0.0
    assert response_age({"age": "invalid"}) == float("inf")


def test_remaining_freshness_bounds_the_retention() -> None:
    """The origin age must reduce the remaining lifetime."""
    headers = {"cache-control": "public, max-age=300", "age": "60"}
    assert response_ttl(headers, 300) == 240


def test_an_aged_response_is_stored_while_it_is_still_fresh() -> None:
    """An aged response with remaining freshness may enter the cache."""
    headers = {"cache-control": "public, max-age=300", "age": "60"}
    assert response_cacheable(headers, is_static=True) is True


def test_a_stale_response_is_refused() -> None:
    """A response that is older than its lifetime must not be stored."""
    headers = {"cache-control": "public, max-age=60", "age": "600"}
    assert response_cacheable(headers, is_static=True) is False


def test_dynamic_responses_still_refuse_an_age_header() -> None:
    """Without an explicit lifetime an aged response stays uncacheable."""
    headers = {"cache-control": "public", "age": "60"}
    assert response_cacheable(headers, is_static=False) is False


def test_engine_stores_an_aged_asset_and_reports_the_total_age() -> None:
    """The stored entry must report the origin age plus the time in the cache."""
    import asyncio

    engine = RocketBooster(origin())
    asyncio.run(call(engine, build_scope("/static/app.css")))
    assert engine.cache.count() == 1
    body, headers = asyncio.run(call(engine, build_scope("/static/app.css")))
    assert body == b"body{}"
    age = [value for name, value in headers if name.lower() == b"age"]
    assert age and int(age[0]) >= 81
