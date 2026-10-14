"""Ultra-fast ASGI Middleware for FastAPI, Starlette, and ASGI frameworks."""

import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from go_fast.cache import FastMemoryCache
from go_fast.compressor import ResponseCompressor
from go_fast.minifier import FastMinifier
from go_fast.telemetry import TelemetryTracker

logger = logging.getLogger("go_fast")


def parse_asgi_headers(raw_headers: List[Tuple[bytes, bytes]]) -> Dict[str, str]:
    """Convert ASGI header tuples to normalized lower-case dict."""
    return {k.decode("latin1").lower(): v.decode("latin1") for k, v in raw_headers}


class RocketBooster:
    """High-speed ASGI middleware combining caching, minification, and compression."""

    def __init__(
        self,
        app: Any,
        cache_ttl: float = 300.0,
        max_cache_items: int = 2000,
        enable_minification: bool = True,
        enable_compression: bool = True,
        min_compress_size: int = 512,
    ) -> None:
        self.app = app
        self.cache = FastMemoryCache(max_items=max_cache_items, default_ttl=cache_ttl)
        self.compressor = ResponseCompressor(min_size=min_compress_size)
        self.minifier = FastMinifier()
        self.telemetry = TelemetryTracker()
        self.enable_minification = enable_minification
        self.enable_compression = enable_compression

    @classmethod
    def attach(cls, app: Any, **kwargs: Any) -> "RocketBooster":
        """Convenient one-line setup for FastAPI or Starlette apps."""
        instance = cls(app=app.router, **kwargs)
        app.add_middleware(cls, **kwargs)
        return instance

    async def __call__(self, scope: Dict[str, Any], receive: Callable, send: Callable) -> None:
        """ASGI request handler routing HTTP requests through optimizer."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET").upper()
        path = scope.get("path", "/")
        headers = parse_asgi_headers(scope.get("headers", []))

        if method in ("POST", "PUT", "DELETE", "PATCH"):
            self.cache.invalidate_path_prefix(path)
            await self.app(scope, receive, send)
            return

        if method == "GET":
            handled = await self._handle_get(scope, receive, send, path, headers)
            if handled:
                return

        await self._passthrough_and_cache(scope, receive, send, path, headers)

    async def _handle_get(
        self,
        scope: Dict[str, Any],
        receive: Callable,
        send: Callable,
        path: str,
        headers: Dict[str, str],
    ) -> bool:
        """Check cache and serve response immediately if valid."""
        query = scope.get("query_string", b"")
        cache_key = self.cache.make_key("GET", path, query)
        cached = self.cache.get(cache_key)
        if not cached:
            return False

        start_time = time.perf_counter()
        if headers.get("if-none-match") == cached.etag:
            await self._send_304(send, cached.etag)
            duration = (time.perf_counter() - start_time) * 1000
            self.telemetry.record_request(
                "GET", path, 304, duration, True, len(cached.body), 0, "none", 150.0
            )
            return True

        body = cached.body
        encoding: Optional[str] = None
        if self.enable_compression:
            body, encoding = self.compressor.compress(
                cached.body, cached.content_type, headers.get("accept-encoding", "")
            )

        await self._send_cached(send, cached.status_code, cached.content_type, body, cached.etag, encoding)
        duration = (time.perf_counter() - start_time) * 1000
        self.telemetry.record_request(
            "GET", path, cached.status_code, duration, True, len(cached.body), len(body), encoding or "none", 120.0
        )
        return True

    async def _send_304(self, send: Callable, etag: str) -> None:
        """Send HTTP 304 Not Modified."""
        headers = [(b"etag", etag.encode("latin1")), (b"cache-control", b"public, max-age=60")]
        await send({"type": "http.response.start", "status": 304, "headers": headers})
        await send({"type": "http.response.body", "body": b""})

    async def _send_cached(
        self,
        send: Callable,
        status: int,
        content_type: str,
        body: bytes,
        etag: str,
        encoding: Optional[str],
    ) -> None:
        """Send complete cached response to client."""
        raw_headers: List[Tuple[bytes, bytes]] = [
            (b"content-type", content_type.encode("latin1")),
            (b"etag", etag.encode("latin1")),
            (b"cache-control", b"public, max-age=120, stale-while-revalidate=60"),
            (b"x-powered-by", b"go_fast RocketBooster"),
        ]
        if encoding:
            raw_headers.append((b"content-encoding", encoding.encode("latin1")))
            raw_headers.append((b"vary", b"Accept-Encoding"))
        raw_headers.append((b"content-length", str(len(body)).encode("latin1")))

        await send({"type": "http.response.start", "status": status, "headers": raw_headers})
        await send({"type": "http.response.body", "body": body})

    async def _passthrough_and_cache(
        self,
        scope: Dict[str, Any],
        receive: Callable,
        send: Callable,
        path: str,
        req_headers: Dict[str, str],
    ) -> None:
        """Execute downstream app, capture response, minify, compress, and cache."""
        start_time = time.perf_counter()
        status_code = 200
        response_headers: List[Tuple[bytes, bytes]] = []
        body_chunks: List[bytes] = []

        async def intercept_send(message: Dict[str, Any]) -> None:
            nonlocal status_code, response_headers
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
                response_headers = list(message.get("headers", []))
            elif message["type"] == "http.response.body":
                chunk = message.get("body", b"")
                if chunk:
                    body_chunks.append(chunk)

        await self.app(scope, receive, intercept_send)
        raw_body = b"".join(body_chunks)
        duration = (time.perf_counter() - start_time) * 1000

        header_dict = parse_asgi_headers(response_headers)
        content_type = header_dict.get("content-type", "text/plain")

        processed_body = raw_body
        if self.enable_minification and status_code == 200:
            processed_body = self.minifier.minify(raw_body, content_type)

        cached_entry = None
        if status_code == 200 and scope.get("method") == "GET" and len(processed_body) < 2_000_000:
            query = scope.get("query_string", b"")
            key = self.cache.make_key("GET", path, query)
            cached_entry = self.cache.set(key, path, status_code, response_headers, processed_body, content_type)

        encoding: Optional[str] = None
        final_body = processed_body
        if self.enable_compression:
            final_body, encoding = self.compressor.compress(
                processed_body, content_type, req_headers.get("accept-encoding", "")
            )

        out_headers = [(k, v) for k, v in response_headers if k.lower() not in (b"content-length", b"content-encoding")]
        out_headers.append((b"content-length", str(len(final_body)).encode("latin1")))
        if cached_entry:
            out_headers.append((b"etag", cached_entry.etag.encode("latin1")))
            out_headers.append((b"cache-control", b"public, max-age=120, stale-while-revalidate=60"))
        if encoding:
            out_headers.append((b"content-encoding", encoding.encode("latin1")))
            out_headers.append((b"vary", b"Accept-Encoding"))
        out_headers.append((b"x-powered-by", b"go_fast RocketBooster"))

        await send({"type": "http.response.start", "status": status_code, "headers": out_headers})
        await send({"type": "http.response.body", "body": final_body})

        self.telemetry.record_request(
            scope.get("method", "GET"),
            path,
            status_code,
            duration,
            False,
            len(raw_body),
            len(final_body),
            encoding or "none",
            0.0,
        )
