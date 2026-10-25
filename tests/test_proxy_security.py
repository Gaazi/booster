"""Proxy transport regressions for isolation, streaming and invalidation races."""

from __future__ import annotations
from typing import Any, Callable, AsyncIterator, Iterator

import asyncio
import gzip
from unittest.mock import patch

import httpx
from starlette.requests import Request
from starlette.responses import StreamingResponse

from booster.proxy import SpeedProxyServer


class ChunkStream(httpx.AsyncByteStream):
    """Expose raw chunks while recording whether the proxy released the stream."""

    def __init__(self, chunks: list[bytes]) -> None:
        """Initialize the stream chunks and connection-close tracking."""
        self.chunks, self.closed = chunks, False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        """Yield the fixture body as raw upstream chunks."""
        for chunk in self.chunks:
            yield chunk

    async def aclose(self) -> None:
        """Record that the upstream connection has been released."""
        self.closed = True


def request(path: str="/site/data", method: str="GET", headers: Any=None, query: bytes=b"") -> Any:
    """Build an isolated request without using the network."""
    result = Request({"type": "http", "method": method, "path": path, "raw_path": path.encode(),
                      "query_string": query, "headers": headers or [], "scheme": "http",
                      "server": ("127.0.0.1", 5051)})
    result._body = b""
    return result


def test_raw_encoded_origin_response_and_duplicate_cookies() -> None:
    """Encoded upstream bytes and separate cookies pass through without decoding."""
    async def scenario() -> None:
        """Exercise the isolated asynchronous proxy scenario."""
        encoded = gzip.compress(b"private" * 500)
        stream = ChunkStream([encoded])
        def origin(req: Any) -> Any:
            """Return the controlled origin response for this scenario."""
            assert req.headers["accept-encoding"] == "identity"
            assert "x-forwarded-for" not in req.headers and "x-secret" not in req.headers
            return httpx.Response(200, stream=stream, headers=[("content-encoding", "gzip"),
                        ("set-cookie", "a=1"), ("set-cookie", "b=2"), ("etag", '"origin"')])
        proxy = SpeedProxyServer("http://origin.test")
        proxy._client = httpx.AsyncClient(transport=httpx.MockTransport(origin))
        response = await proxy.handle_request(request(headers=[(b"x-forwarded-for", b"spoofed"),
                                         (b"connection", b"x-secret"), (b"x-secret", b"secret")]))
        assert response.body == encoded and stream.closed
        assert response.headers["content-encoding"] == "gzip"
        assert response.headers.getlist("set-cookie") == ["a=1", "b=2"]
        assert response.headers["etag"] == '"origin"'
        assert proxy.cache.count() == 0
        await proxy.close()
    asyncio.run(scenario())


def test_large_origin_response_is_streamed_and_closed() -> None:
    """Responses exceeding the buffer limit stream and never enter the cache."""
    async def scenario() -> None:
        """Exercise the isolated asynchronous proxy scenario."""
        stream = ChunkStream([b"x" * 100_000 for _ in range(30)])
        proxy = SpeedProxyServer("http://origin.test")
        proxy._client = httpx.AsyncClient(transport=httpx.MockTransport(lambda req:
            httpx.Response(200, stream=stream, headers={"cache-control": "public", "content-type": "text/plain"})))
        response = await proxy.handle_request(request())
        assert isinstance(response, StreamingResponse) and not stream.closed
        size = 0
        async for chunk in response.body_iterator:
            size += len(chunk)
        assert size == 3_000_000 and stream.closed and proxy.cache.count() == 0
        await proxy.close()
    asyncio.run(scenario())


def test_large_upload_rejected_before_origin_request() -> None:
    """Request-body bounds apply before credentials or content reach the origin."""
    async def scenario() -> None:
        """Exercise the isolated asynchronous proxy scenario."""
        proxy = SpeedProxyServer("http://origin.test")
        incoming = request(method="POST")
        incoming._body = b"x" * 8_000_001
        assert (await proxy.handle_request(incoming)).status_code == 413
        assert proxy._client is None
    asyncio.run(scenario())


def test_target_change_during_fetch_cannot_repopulate_cache() -> None:
    """A pending old-target response is excluded after the target changes."""
    async def scenario() -> None:
        """Exercise the isolated asynchronous proxy scenario."""
        proxy = SpeedProxyServer("http://old.test")
        def origin(req: Any) -> Any:
            """Return the controlled origin response for this scenario."""
            proxy.set_target("http://new.test")
            return httpx.Response(200, stream=ChunkStream([b"old"]), headers={"cache-control": "public"})
        proxy._client = httpx.AsyncClient(transport=httpx.MockTransport(origin))
        assert (await proxy.handle_request(request())).body == b"old"
        assert proxy.cache.count() == 0
        await proxy.close()
    asyncio.run(scenario())


def test_client_does_not_retain_cookies_or_environment_proxies() -> None:
    """The real pooled-client policy retains no cross-user credentials."""
    async def scenario() -> None:
        """Exercise the isolated asynchronous proxy scenario."""
        original_client = httpx.AsyncClient
        def client_factory(**kwargs) -> Any:
            """Build the pooled client with a controlled origin transport."""
            assert kwargs["trust_env"] is False
            return original_client(**kwargs, transport=httpx.MockTransport(lambda req:
                httpx.Response(200, stream=ChunkStream([b"private"]), headers={"set-cookie": "secret=one"})))
        proxy = SpeedProxyServer("http://origin.test")
        with patch("booster.proxy.httpx.AsyncClient", side_effect=client_factory):
            await proxy.handle_request(request())
            assert len(proxy.get_client().cookies) == 0
            await proxy.close()
    asyncio.run(scenario())


def test_public_proxy_etag_consistent_across_miss_hit_and_304() -> None:
    """Validators and negotiation headers match every public representation."""
    async def scenario() -> None:
        """Exercise the isolated asynchronous proxy scenario."""
        proxy = SpeedProxyServer("http://origin.test")
        calls = []
        def origin(req: Any) -> Any:
            """Return the controlled origin response for this scenario."""
            calls.append(req)
            return httpx.Response(200, stream=ChunkStream([b'{ "value": 1 }']), headers={
                "cache-control": "public", "content-type": "application/json", "etag": '"old"', "digest": "old"})
        proxy._client = httpx.AsyncClient(transport=httpx.MockTransport(origin))
        first = await proxy.handle_request(request())
        second = await proxy.handle_request(request())
        third = await proxy.handle_request(request(headers=[(b"if-none-match", first.headers["etag"].encode())]))
        assert first.body == second.body == b'{"value":1}'
        assert first.headers["etag"] == second.headers["etag"] != '"old"'
        assert "digest" not in first.headers and third.status_code == 304
        assert len(calls) == 1
        await proxy.close()
    asyncio.run(scenario())
