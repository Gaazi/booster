"""Conservative ASGI caching and compression for explicitly public responses."""

import time
from typing import Any, Callable

from booster.asgi_response import ASGIResponseOptimizer, parse_headers, representation_headers
from booster.http_policy import request_cacheable
from booster.cache import FastMemoryCache
from booster.compressor import ResponseCompressor
from booster.minifier import FastMinifier
from booster.telemetry import TelemetryTracker
from booster.cache_policy import CachePolicy
from booster.invalidation import FULL_CLEAR, InvalidationBus
from booster.bypass import BypassTracker
from booster.bypass import CREDENTIALS as BYPASS_CREDENTIALS
from booster.bypass import METHOD as BYPASS_METHOD
from booster.bypass import PERSONALIZED as BYPASS_PERSONALIZED
from booster.bypass import POLICY as BYPASS_POLICY
from booster.bypass import REQUEST_DIRECTIVE as BYPASS_REQUEST_DIRECTIVE

parse_asgi_headers = parse_headers


class RocketBooster:
    """Accelerate public and static responses and adaptively optimize dynamic traffic."""

    def __init__(self, app: Any, cache_ttl: float = 300.0, max_cache_items: int = 2000,
                 enable_minification: bool = True, enable_compression: bool = True,
                 min_compress_size: int = 512, compress_dynamic: bool = False,
                 surgical_invalidation: bool = False,
                 cache_policy: CachePolicy | None = None,
                 max_cache_bytes: int = 64 * 1024 * 1024,
                 invalidation_bus: InvalidationBus | None = None,
                 _instance: "RocketBooster | None" = None) -> None:
        """Initialize bounded caches or share the instance exposed by attach."""
        if _instance is not None:
            self.__dict__.update(_instance.__dict__)
            self.app = app
            return
        self.app = app
        self.cache = FastMemoryCache(max_items=max_cache_items, default_ttl=cache_ttl,
                                     max_bytes=max_cache_bytes)
        self.compressor = ResponseCompressor(min_size=min_compress_size)
        self.minifier = FastMinifier()
        self.telemetry = TelemetryTracker()
        self.bypass = BypassTracker()
        self.enable_minification = enable_minification
        self.enable_compression = enable_compression
        self.compress_dynamic = compress_dynamic
        self.surgical_invalidation = surgical_invalidation
        self.cache_policy = cache_policy or CachePolicy()
        self.invalidation_bus = invalidation_bus

    @classmethod
    def attach(cls, app: Any, **kwargs: Any) -> "RocketBooster":
        """Register middleware and expose the cache actually serving the app."""
        if any(layer.cls is cls for layer in app.user_middleware):
            raise ValueError("Booster is already attached to this application")
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
        self.apply_pending_invalidations()
        method = scope.get("method", "GET").upper()
        path = scope.get("path", "/")
        if method in ("POST", "PUT", "DELETE", "PATCH"):
            await self._handle_mutation(scope, receive, send)
            return
        headers = parse_headers(scope.get("headers", []))
        if method != "GET" or not self.cache_policy.allows(path):
            self.bypass.record(BYPASS_METHOD if method != "GET" else BYPASS_POLICY)
            await self.app(scope, receive, send)
            return

        reason = self._bypass_reason(scope, headers)
        if reason is not None:
            self.bypass.record(reason)
            if self.compress_dynamic:
                await self._passthrough_and_cache(scope, receive, send, path, headers)
            else:
                await self.app(scope, receive, send)
            return

        if await self._handle_get(scope, receive, send, path, headers):
            return
        await self._passthrough_and_cache(scope, receive, send, path, headers)

    def _bypass_reason(self, scope: dict[str, Any], headers: dict[str, str]) -> str | None:
        """Explain why this request may not use the shared cache."""
        if any(scope.get(key) for key in ("user", "auth", "session")):
            return BYPASS_PERSONALIZED
        if headers.get("cookie") or headers.get("authorization"):
            return BYPASS_CREDENTIALS
        if not request_cacheable(headers):
            return BYPASS_REQUEST_DIRECTIVE
        return None

    async def _handle_mutation(self, scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        """Invalidate before and after writes, including failed or concurrent writes."""
        path = scope.get("path", "/")
        self.bypass.record(BYPASS_METHOD)
        self._invalidate(path)
        try:
            await self.app(scope, receive, send)
        finally:
            self._invalidate(path)

    def _invalidate(self, path: str) -> None:
        """Keep full invalidation safe by default for cross-route dependencies."""
        if self.surgical_invalidation:
            self.cache.invalidate_path_prefix(path)
            self.publish_invalidation(path)
        else:
            self.cache.clear()
            self.publish_invalidation(FULL_CLEAR)

    def publish_invalidation(self, prefix: str) -> None:
        """Tell the other workers that cached reads are no longer valid."""
        if self.invalidation_bus is not None:
            self.invalidation_bus.publish(prefix)

    def apply_pending_invalidations(self) -> None:
        """Apply the invalidation notices published by the other workers."""
        if self.invalidation_bus is None:
            return
        for notice in self.invalidation_bus.drain():
            if notice == FULL_CLEAR:
                self.cache.clear()
            else:
                self.cache.invalidate_path_prefix(notice)

    def clear_cache(self) -> None:
        """Clear the local cache and tell the other workers to clear theirs."""
        self.cache.clear()
        self.publish_invalidation(FULL_CLEAR)

    async def _handle_get(self, scope: dict[str, Any], receive: Callable, send: Callable,
                          path: str, headers: dict[str, str]) -> bool:
        """Serve a public cached representation or its conditional response."""
        cached = self.cache.get(self.cache_key(scope, headers))
        if cached is None:
            return False
        start = time.perf_counter()
        if headers.get("if-none-match") == cached.etag:
            await self._send_304(send, cached)
            size, encoding, status = 0, None, 304
        else:
            body, encoding = cached.body, None
            if self.enable_compression:
                body, encoding = self.compressor.compress(body, cached.content_type,
                                                          headers.get("accept-encoding", ""))
            stored_headers = cached.headers + [(b"age", str(int(time.monotonic() - cached.created_at)).encode("ascii"))]
            await self._send_cached(send, cached.status_code, cached.content_type, body,
                                    cached.etag, encoding, stored_headers)
            size, status = len(body), cached.status_code
        self.telemetry.record_request("GET", "[redacted]", status,
                                     (time.perf_counter() - start) * 1000, True,
                                     len(cached.body), size, encoding or "none")
        return True

    async def _send_304(self, send: Callable, cached: Any) -> None:
        """Retain origin cache and security headers on conditional cache hits."""
        headers = representation_headers(cached.headers, b"", cached.etag, None)
        headers = [(key, value) for key, value in headers if key.lower() not in
                   {b"content-length", b"content-type"}]
        headers.append((b"age", str(int(time.monotonic() - cached.created_at)).encode("ascii")))
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

    def get_status(self) -> dict[str, Any]:
        """Return a host-dashboard snapshot without credentials, URLs or payloads."""
        from booster import __version__
        metrics = self.telemetry.get_stats()
        metrics.pop("recent_logs", None)
        metrics["bypass_reasons"] = self.bypass.get_counts()
        return {
            "active": True, "version": __version__, "cache": self.cache.get_stats(),
            "metrics": metrics,
            "configuration": {
                "cache_ttl_seconds": self.cache.default_ttl,
                "include_paths": self.cache_policy.include_paths,
                "exclude_paths": self.cache_policy.exclude_paths,
                "compression": self.enable_compression,
                "minification": self.enable_minification,
                "dynamic_compression": self.compress_dynamic,
                "surgical_invalidation": self.surgical_invalidation,
                "invalidation": "shared" if self.invalidation_bus else "process",
            },
        }
