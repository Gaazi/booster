"""Universal high-speed Reverse Proxy and Caching Accelerator."""

import logging
import time
from typing import Any, Callable, Dict, Optional, Tuple

import httpx
from starlette.requests import Request
from starlette.responses import Response

from go_fast.cache import FastMemoryCache
from go_fast.compressor import ResponseCompressor
from go_fast.minifier import FastMinifier
from go_fast.telemetry import TelemetryTracker

logger = logging.getLogger("go_fast.proxy")


class SpeedProxyServer:
    """Universal reverse proxy that accelerates any target web server."""

    def __init__(self, target_url: str = "http://127.0.0.1:8000") -> None:
        self.target_url = target_url.rstrip("/")
        self.cache = FastMemoryCache(max_items=2000, default_ttl=300.0)
        self.compressor = ResponseCompressor(min_size=256)
        self.minifier = FastMinifier()
        self.telemetry = TelemetryTracker()
        self._client: Optional[httpx.AsyncClient] = None

    def get_client(self) -> httpx.AsyncClient:
        """Return pooled async HTTP client for connection reuse."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        return self._client

    def set_target(self, new_url: str) -> None:
        """Update upstream target URL and reset cache."""
        self.target_url = new_url.rstrip("/")
        self.cache.clear()

    async def handle_request(self, request: Request) -> Response:
        """Intercept, cache, optimize, and proxy incoming client request."""
        method = request.method.upper()
        path = request.url.path
        query = request.url.query.encode("latin1")

        if method in ("POST", "PUT", "DELETE", "PATCH"):
            self.cache.invalidate_path_prefix(path)
            return await self._proxy_upstream(request, path)

        if method == "GET":
            cached_resp = self._check_cache(request, path, query)
            if cached_resp is not None:
                return cached_resp

        return await self._fetch_and_cache(request, path, query)

    def _check_cache(self, request: Request, path: str, query: bytes) -> Optional[Response]:
        """Check cache and return 304 or cached content if valid."""
        cache_key = self.cache.make_key("GET", path, query)
        cached = self.cache.get(cache_key)
        if not cached:
            return None

        start_time = time.perf_counter()
        if request.headers.get("if-none-match") == cached.etag:
            duration = (time.perf_counter() - start_time) * 1000
            self.telemetry.record_request(
                "GET", path, 304, duration, True, len(cached.body), 0, "none", 120.0
            )
            return Response(status_code=304, headers={"ETag": cached.etag})

        body, encoding = self.compressor.compress(
            cached.body, cached.content_type, request.headers.get("accept-encoding", "")
        )
        headers = {
            "Content-Type": cached.content_type,
            "ETag": cached.etag,
            "Cache-Control": "public, max-age=120",
            "X-Accelerated-By": "go_fast Rocket Proxy",
        }
        if encoding:
            headers["Content-Encoding"] = encoding
            headers["Vary"] = "Accept-Encoding"

        duration = (time.perf_counter() - start_time) * 1000
        self.telemetry.record_request(
            "GET", path, cached.status_code, duration, True, len(cached.body), len(body), encoding or "none", 100.0
        )
        return Response(content=body, status_code=cached.status_code, headers=headers)

    async def _fetch_and_cache(self, request: Request, path: str, query: bytes) -> Response:
        """Fetch from origin server, minify, compress, and store in cache."""
        upstream_url = f"{self.target_url}{path}"
        if query:
            upstream_url = f"{upstream_url}?{query.decode('latin1')}"

        client = self.get_client()
        start = time.perf_counter()
        try:
            res = await client.request(
                method=request.method,
                url=upstream_url,
                headers=dict(request.headers),
                content=await request.body(),
            )
        except Exception as exc:
            logger.error("Upstream connection error: %s", exc)
            return Response(f"go_fast Proxy Gateway Error: {exc}", status_code=502)

        upstream_duration = (time.perf_counter() - start) * 1000
        raw_body = res.content
        content_type = res.headers.get("content-type", "text/plain")

        processed = self.minifier.minify(raw_body, content_type)
        if res.status_code == 200 and request.method == "GET" and len(processed) < 3_000_000:
            key = self.cache.make_key("GET", path, query)
            self.cache.set(key, path, res.status_code, [], processed, content_type)

        compressed, encoding = self.compressor.compress(
            processed, content_type, request.headers.get("accept-encoding", "")
        )
        out_headers = {k: v for k, v in res.headers.items() if k.lower() not in ("content-length", "content-encoding")}
        out_headers["X-Accelerated-By"] = "go_fast Rocket Proxy"
        if encoding:
            out_headers["Content-Encoding"] = encoding
            out_headers["Vary"] = "Accept-Encoding"

        self.telemetry.record_request(
            request.method, path, res.status_code, upstream_duration, False, len(raw_body), len(compressed), encoding or "none"
        )
        return Response(content=compressed, status_code=res.status_code, headers=out_headers)

    async def _proxy_upstream(self, request: Request, path: str) -> Response:
        """Direct passthrough for write mutations."""
        client = self.get_client()
        upstream_url = f"{self.target_url}{path}"
        res = await client.request(
            method=request.method,
            url=upstream_url,
            headers=dict(request.headers),
            content=await request.body(),
        )
        return Response(content=res.content, status_code=res.status_code, headers=dict(res.headers))
