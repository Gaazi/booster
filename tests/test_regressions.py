"""Regression coverage for HTTP correctness, security and optimization."""

from __future__ import annotations
from typing import Any, Callable, AsyncIterator, Iterator

import asyncio
import gzip
from unittest.mock import patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.responses import Response, StreamingResponse
from starlette.requests import Request
from starlette.testclient import TestClient

from go_fast.booster import RocketBooster
from go_fast.cache import FastMemoryCache
from go_fast.compressor import choose_encoding, compress_payload
from go_fast.minifier import minify_html, minify_css
from go_fast.proxy import SpeedProxyServer


@pytest.mark.parametrize("header,expected", [
    ("gzip;q=0, br;q=0", None), ("gzip;q=1, br;q=0.2", "gzip"),
    ("xgzip", None), ("gzip;q=bad", None), ("gzip;q=0, *;q=1", "br"),
])
def test_encoding_quality(header: str, expected: str | None) -> None:
    """Honor explicit exclusions, quality and exact encoding tokens."""
    assert choose_encoding(header) == expected


def test_compression_reuses_work() -> None:
    """Repeated payloads reuse bounded compressed representations."""
    compress_payload.cache_clear()
    with patch("go_fast.compressor.gzip.compress", wraps=gzip.compress) as compressor:
        assert compress_payload(b"x" * 2048, "gzip") == compress_payload(b"x" * 2048, "gzip")
        assert compressor.call_count == 1


@pytest.mark.parametrize("markup", ["<pre>  a\n b  </pre>",
    '<script>const x = "<!-- preserve -->";</script>', "<textarea> a\n b </textarea>"])
def test_protected_html(markup: str) -> None:
    """Minification preserves whitespace-sensitive elements."""
    assert minify_html(markup) == markup


def test_quoted_css() -> None:
    """Comment markers and punctuation inside strings stay unchanged."""
    assert minify_css('a { content: "/*keep*/ a ; b"; }') == 'a { content: "/*keep*/ a ; b"; }'


@pytest.mark.parametrize("response_headers", [
    {"cache-control": "private"}, {"cache-control": "no-store"},
    {"vary": "Accept-Language"}, {"set-cookie": "session=secret"},
])
def test_private_responses_not_cached(response_headers: dict[str, str]) -> None:
    """Private or varying responses always reach the origin."""
    app = FastAPI()
    calls = []
    @app.get("/")
    def endpoint() -> Any:
        """Return the fixture response exercised by this regression."""
        calls.append(1)
        return Response(str(len(calls)), headers=response_headers)
    client = TestClient(RocketBooster(app))
    assert client.get("/").text == "1"
    assert client.get("/").text == "2"


def test_authenticated_request_bypasses_public_cache() -> None:
    """An authorization request cannot receive another user's cached content."""
    app = FastAPI()
    @app.get("/")
    def endpoint(request: Request) -> Any:
        """Return the fixture response exercised by this regression."""
        return Response(request.headers.get("authorization", "public"), headers={"cache-control": "public"})
    client = TestClient(RocketBooster(app))
    assert client.get("/").text == "public"
    assert client.get("/", headers={"authorization": "secret"}).text == "secret"
    assert client.get("/").text == "public"


def test_streaming_messages_forwarded() -> None:
    """Streaming chunks reach send before the application completes."""
    messages = []
    async def app(scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        """Emit controlled ASGI messages for the streaming regression."""
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"cache-control", b"public")]})
        await send({"type": "http.response.body", "body": b"one", "more_body": True})
        assert len(messages) == 2
        await send({"type": "http.response.body", "body": b"two"})
    async def send(message: dict[str, Any]) -> None:
        """Capture an ASGI response message for assertions."""
        messages.append(message)
    asyncio.run(RocketBooster(app)({"type": "http", "method": "GET", "path": "/"}, None, send))
    assert messages[-1]["body"] == b"two"


def test_proxy_routes_queries_and_isolates_cookies() -> None:
    """Gateway strips its prefix and never forwards another user's cookies."""
    async def scenario() -> None:
        """Exercise the isolated asynchronous proxy scenario."""
        received = []
        def upstream(request: Any) -> Any:
            """Return a controlled response while observing upstream requests."""
            received.append(request)
            return httpx.Response(200, text="ok", headers={"set-cookie": "secret=one"})
        proxy = SpeedProxyServer("http://origin.test")
        proxy._client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
        for method in ("GET", "POST"):
            request = Request({"type": "http", "method": method, "path": "/site/items",
                               "query_string": b"page=2", "headers": [], "scheme": "http",
                               "server": ("localhost", 5050)})
            request._body = b""
            assert (await proxy.handle_request(request)).status_code == 200
        assert all(str(r.url) == "http://origin.test/items?page=2" for r in received)
        assert all("cookie" not in r.headers for r in received)
        await proxy.close()
    asyncio.run(scenario())


def test_cache_capacity_validation() -> None:
    """Reject an invalid cache capacity before eviction can fail."""
    with pytest.raises(ValueError):
        FastMemoryCache(max_items=0)


def test_proxy_compressed_and_cached_headers() -> None:
    """Compressed miss and hit retain origin headers and valid payloads."""
    async def scenario() -> None:
        """Exercise the isolated asynchronous proxy scenario."""
        proxy = SpeedProxyServer("http://origin.test")
        def upstream(request: Any) -> Any:
            """Return a controlled response while observing upstream requests."""
            return httpx.Response(200, content=b"x" * 2048,
                                  headers={"content-type": "text/plain", "x-origin": "kept", "cache-control": "public"})
        proxy._client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
        scope = {"type": "http", "method": "GET", "path": "/site/data", "query_string": b"",
                 "headers": [(b"accept-encoding", b"gzip")], "scheme": "http",
                 "server": ("localhost", 5050)}
        for _ in range(2):
            request = Request(scope)
            request._body = b""
            response = await proxy.handle_request(request)
            assert gzip.decompress(response.body) == b"x" * 2048
            assert response.headers["x-origin"] == "kept"
            assert response.headers["vary"] == "Accept-Encoding"
        await proxy.close()
    asyncio.run(scenario())


def test_attach_returns_active_cache() -> None:
    """The convenience API exposes the cache actually serving requests."""
    app = FastAPI()
    @app.get("/")
    def endpoint() -> Any:
        """Return the fixture response exercised by this regression."""
        return Response("ok", headers={"cache-control": "public"})
    booster = RocketBooster.attach(app)
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert booster.cache.count() == 1


@pytest.mark.parametrize("url", ["file:///tmp/secret", "javascript:alert(1)",
    "http://", "https://example.test/?q=1"])
def test_invalid_target_rejected(url: str) -> None:
    """Dashboard accepts only well-formed HTTP base targets."""
    from run import app
    assert TestClient(app, base_url="http://127.0.0.1:5050", client=("127.0.0.1", 12345)).post("/api/set-target", json={"url": url}, headers={"X-Go-Fast-Admin": "1"}).status_code == 400


def test_host_cache_isolation() -> None:
    """Different virtual hosts cannot share a response cache entry."""
    app = FastAPI()
    @app.get("/")
    def endpoint(request: Request) -> Any:
        """Return the fixture response exercised by this regression."""
        return Response(request.headers["host"], headers={"cache-control": "public"})
    client = TestClient(RocketBooster(app))
    assert client.get("/", headers={"host": "one.test"}).text == "one.test"
    assert client.get("/", headers={"host": "two.test"}).text == "two.test"


def test_precompressed_asgi_response() -> None:
    """Already encoded responses retain their encoding and body."""
    app = FastAPI()
    @app.get("/")
    def endpoint() -> Any:
        """Return the fixture response exercised by this regression."""
        return Response(gzip.compress(b"keep payload"), headers={"content-encoding": "gzip"})
    response = TestClient(RocketBooster(app)).get("/")
    assert response.content == b"keep payload"
    assert response.headers["content-encoding"] == "gzip"
