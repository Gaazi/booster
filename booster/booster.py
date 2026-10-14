"""Conservative ASGI caching and compression for explicitly public responses."""

import time
from typing import Any, Callable

from booster.asgi_response import ASGIResponseOptimizer, parse_headers, representation_headers
from booster.http_policy import request_cacheable
from booster.cache import FastMemoryCache
from booster.compressor import ResponseCompressor
from booster.minifier import FastMinifier
from booster.telemetry import TelemetryTracker

parse_asgi_headers = parse_headers


class RocketBooster:
    """Accelerate public responses while leaving personalized traffic untouched."""

    def __init__(self, app: Any, cache_ttl: float = 300.0, max_cache_items: int = 2000,
                 enable_minification: bool = True, enable_compression: bool = True,
                 min_compress_size: int = 512, _instance: "RocketBooster | None" = None) -> None:
        """Initialize bounded caches or share the instance exposed by attach."""
        if _instance is not None:
            self.__dict__.update(_instance.__dict__)
            self.app = app
            return
        self.app = app
        self.cache = FastMemoryCache(max_items=max_cache_items, default_ttl=cache_ttl)
        self.compressor = ResponseCompressor(min_size=min_compress_size)
        self.minifier = FastMinifier()
        self.telemetry = TelemetryTracker()
        self.enable_minification = enable_minification
        self.enable_compression = enable_compression

    @classmethod
    def attach(cls, app: Any, **kwargs: Any) -> "RocketBooster":
        """Register middleware and expose the cache actually serving the app."""
        instance = cls(app=app.router, **kwargs)
        app.add_middleware(cls, _instance=instance, **kwargs)
        return instance

    def cache_key(self, scope: dict[str, Any], headers: dict[str, str]) -> str:
        """Isolate representations by scheme, host, path and query."""
        authority = scope.get("scheme", "http") + ":" + headers.get("host", "")
        raw_path = scope.get("raw_path", scope.get("path", "/").encode("utf-8")).decode("latin1")
        return self.cache.make_key("GET:" + authority, raw_path,
                                   scope.get("query_string", b""))

    async def __call__(self, scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        """Bypass private requests and invalidate cached reads around mutations."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        method = scope.get("method", "GET").upper()
        if method in ("POST", "PUT", "DELETE", "PATCH"):
            self.cache.clear()
            try:
                await self.app(scope, receive, send)
            finally:
                self.cache.clear()
            return
        headers = parse_headers(scope.get("headers", []))
        if (method != "GET" or not request_cacheable(headers)
                or any(scope.get(key) for key in ("user", "auth", "session"))):
            await self.app(scope, receive, send)
            return
        if await self._handle_get(scope, receive, send, scope.get("path", "/"), headers):
            return
        await self._passthrough_and_cache(scope, receive, send, scope.get("path", "/"), headers)

    async def _handle_get(self, scope: dict[str, Any], receive: Callable, send: Callable,
                          path: str, headers: dict[str, str]) -> bool:
        """Serve a public cached representation or its conditional response."""
        cached = self.cache.get(self.cache_key(scope, headers))
        if cached is None:
            return False
        start = time.perf_counter()
        if headers.get("if-none-match") == cached.etag:
            await self._send_304(send, cached.etag)
            size, encoding, status = 0, None, 304
        else:
            body, encoding = cached.body, None
            if self.enable_compression:
                body, encoding = self.compressor.compress(body, cached.content_type,
                                                          headers.get("accept-encoding", ""))
            await self._send_cached(send, cached.status_code, cached.content_type, body,
                                    cached.etag, encoding, cached.headers)
            size, status = len(body), cached.status_code
        self.telemetry.record_request("GET", "[redacted]", status,
                                     (time.perf_counter() - start) * 1000, True,
                                     len(cached.body), size, encoding or "none")
        return True

    async def _send_304(self, send: Callable, etag: str) -> None:
        """Send a public conditional response without a payload."""
        headers = [(b"etag", etag.encode("ascii")), (b"vary", b"Accept-Encoding"),
                   (b"cache-control", b"public")]
        await send({"type": "http.response.start", "status": 304, "headers": headers})
        await send({"type": "http.response.body", "body": b""})

    async def _send_cached(self, send: Callable, status: int, content_type: str, body: bytes,
                           etag: str, encoding: str | None,
                           stored_headers: list[tuple[bytes, bytes]]) -> None:
        """Send cached content with validators matching the transformed bytes."""
        headers = representation_headers(stored_headers, body, etag, encoding)
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": body})

    async def _passthrough_and_cache(self, scope: dict[str, Any], receive: Callable,
                                     send: Callable, path: str, req_headers: dict[str, str]) -> None:
        """Optimize a bounded response while respecting ASGI streaming semantics."""
        await self.app(scope, receive, ASGIResponseOptimizer(self, scope, send))
