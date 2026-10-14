"""Conservative ASGI caching and compression for explicitly public responses."""

import time
from typing import Any, Callable

from go_fast.asgi_response import ASGIResponseOptimizer, parse_headers, representation_headers
from go_fast.http_policy import request_cacheable, is_static_asset
from go_fast.cache import FastMemoryCache
from go_fast.compressor import ResponseCompressor
from go_fast.minifier import FastMinifier
from go_fast.telemetry import TelemetryTracker

parse_asgi_headers = parse_headers


class RocketBooster:
    """Accelerate public and static responses and adaptively optimize dynamic traffic."""

    def __init__(self, app: Any, cache_ttl: float = 300.0, max_cache_items: int = 2000,
                 enable_minification: bool = True, enable_compression: bool = True,
                 min_compress_size: int = 512, compress_dynamic: bool = False,
                 surgical_invalidation: bool = False,
                 _instance: "RocketBooster | None" = None) -> None:
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
        self.compress_dynamic = compress_dynamic
        self.surgical_invalidation = surgical_invalidation

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
        """Accelerate static and public reads, optimize dynamic responses, and handle mutations."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        method = scope.get("method", "GET").upper()
        path = scope.get("path", "/")
        if method in ("POST", "PUT", "DELETE", "PATCH"):
            if self.surgical_invalidation:
                self.cache.invalidate_path_prefix(path)
            else:
                self.cache.clear()
            try:
                await self.app(scope, receive, send)
            finally:
                if self.surgical_invalidation:
                    self.cache.invalidate_path_prefix(path)
                else:
                    self.cache.clear()
            return
        headers = parse_headers(scope.get("headers", []))
        if method != "GET":
            await self.app(scope, receive, send)
            return

        is_static = is_static_asset(path)
        if not is_static and (not request_cacheable(headers, is_static=False)
                or any(scope.get(key) for key in ("user", "auth", "session"))):
            if self.compress_dynamic:
                await self._passthrough_and_cache(scope, receive, send, path, headers)
            else:
                await self.app(scope, receive, send)
            return

        if await self._handle_get(scope, receive, send, path, headers):
            return
        await self._passthrough_and_cache(scope, receive, send, path, headers)

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
