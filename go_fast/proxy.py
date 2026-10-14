"""Universal high-speed Reverse Proxy and Caching Accelerator."""

import logging
import time
from typing import Any, Callable, Dict, Optional, Tuple

import httpx
from starlette.requests import Request
from starlette.responses import Response

from go_fast.http_policy import HOP_HEADERS, request_cacheable, response_cacheable, merge_vary
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
            self._client = httpx.AsyncClient(timeout=30.0, follow_redirects=False)
        return self._client

    def set_target(self, new_url: str) -> None:
        """Update upstream target URL and reset cache."""
        self.target_url = new_url.rstrip("/")
        self.cache.clear()

    async def handle_request(self, request: Request) -> Response:
        """Intercept, cache, optimize, and proxy incoming client request."""
        method = request.method.upper()
        path = request.url.path
        if path.startswith("/site/"):
            path = path[5:]
        query = request.url.query.encode("latin1")

        if method in ("POST", "PUT", "DELETE", "PATCH"):
            self.cache.invalidate_path_prefix(path)
            return await self._fetch_and_cache(request, path, query)

        if method == "GET" and request_cacheable(dict(request.headers)):
            cached_resp = self._check_cache(request, path, query)
            if cached_resp is not None:
                return cached_resp

        return await self._fetch_and_cache(request, path, query)

    def _check_cache(self, request: Request, path: str, query: bytes) -> Optional[Response]:
        """Check cache and return 304 or cached content if valid."""
        cache_key = self.cache.make_key("GET:" + request.headers.get("host", ""), path, query)
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
        headers = {k.decode("latin1"): v.decode("latin1") for k, v in cached.headers}
        headers.update({
            "Content-Type": cached.content_type,
            "ETag": cached.etag,
            "X-Accelerated-By": "go_fast Rocket Proxy",
        })
        headers.pop("etag", None)
        headers["vary"] = merge_vary(headers.get("vary", ""))
        if encoding:
            headers["Content-Encoding"] = encoding
            headers["vary"] = merge_vary(headers.get("vary", ""))

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
            outgoing = client.build_request(
                request.method, upstream_url,
                headers={k: v for k, v in request.headers.items() if k.lower() not in HOP_HEADERS},
                content=await request.body(),
            )
            outgoing.headers.pop("cookie", None)
            if "cookie" in request.headers:
                outgoing.headers["cookie"] = request.headers["cookie"]
            res = await client.send(outgoing)
        except httpx.RequestError as exc:
            logger.error("Upstream connection error: %s", exc)
            return Response("Upstream server unavailable", status_code=502)

        upstream_duration = (time.perf_counter() - start) * 1000
        raw_body = res.content
        content_type = res.headers.get("content-type", "text/plain")

        transform = res.status_code == 200 and "no-transform" not in res.headers.get("cache-control", "")
        processed = self.minifier.minify(raw_body, content_type) if transform else raw_body
        if (res.status_code == 200 and request.method == "GET" and len(processed) < 3_000_000
                and request_cacheable(dict(request.headers)) and response_cacheable(dict(res.headers))):
            key = self.cache.make_key("GET:" + request.headers.get("host", ""), path, query)
            self.cache.set(key, path, res.status_code,
                           [(k.encode("latin1"), v.encode("latin1")) for k, v in res.headers.multi_items()
                            if k.lower() not in HOP_HEADERS | {"content-length", "content-encoding"}],
                           processed, content_type)

        compressed, encoding = (self.compressor.compress(
            processed, content_type, request.headers.get("accept-encoding", "")
        ) if transform else (processed, None))
        out_headers = {k: v for k, v in res.headers.items() if k.lower() not in HOP_HEADERS | {"content-length", "content-encoding"}}
        out_headers["X-Accelerated-By"] = "go_fast Rocket Proxy"
        out_headers["vary"] = merge_vary(out_headers.get("vary", ""))
        if encoding:
            out_headers["Content-Encoding"] = encoding
            out_headers["vary"] = merge_vary(out_headers.get("vary", ""))

        self.telemetry.record_request(
            request.method, path, res.status_code, upstream_duration, False, len(raw_body), len(compressed), encoding or "none"
        )
        response = Response(content=compressed, status_code=res.status_code, headers=out_headers)
        response.raw_headers = [(k, v) for k, v in response.raw_headers if k != b"set-cookie"]
        response.raw_headers.extend((b"set-cookie", value.encode("latin1"))
                                    for value in res.headers.get_list("set-cookie"))
        return response

    async def close(self) -> None:
        """Release upstream pooled connections on shutdown."""
        if self._client is not None:
            await self._client.aclose()
