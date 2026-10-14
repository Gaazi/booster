"""Loopback reverse proxy with bounded transport and public response caching."""

import asyncio
import logging
import time
from http.cookiejar import CookieJar, DefaultCookiePolicy
from typing import Any

import httpx
from starlette.requests import Request
from starlette.responses import Response

from go_fast.asgi_response import parse_headers, representation_headers
from go_fast.http_policy import filtered_headers, request_cacheable, response_cacheable
from go_fast.cache import FastMemoryCache
from go_fast.compressor import ResponseCompressor
from go_fast.minifier import FastMinifier
from go_fast.telemetry import TelemetryTracker
from go_fast.local_security import validate_target
from go_fast.proxy_transport import BodyTooLarge, outgoing_headers, request_body, upstream_body

logger = logging.getLogger("go_fast.proxy")


class RejectCookies(DefaultCookiePolicy):
    """Never retain upstream credentials in a shared connection pool."""

    def set_ok(self, cookie: Any, request: Any) -> bool:
        """Reject every upstream cookie; clients manage their own cookie state."""
        return False


class SpeedProxyServer:
    """Accelerate public origin responses without retaining personalized bodies."""

    def __init__(self, target_url: str = "http://127.0.0.1:8000") -> None:
        """Initialize a trusted target and resource limits."""
        self.target_url = validate_target(target_url)
        self.cache = FastMemoryCache(max_items=2000, default_ttl=300.0)
        self.compressor = ResponseCompressor(min_size=256)
        self.minifier = FastMinifier()
        self.telemetry = TelemetryTracker()
        self._client: httpx.AsyncClient | None = None
        self._requests = asyncio.Semaphore(16)

    def get_client(self) -> httpx.AsyncClient:
        """Reuse connections without environment proxies or a shared cookie jar."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0, follow_redirects=False, trust_env=False,
                                             cookies=CookieJar(policy=RejectCookies()),
                                             limits=httpx.Limits(max_connections=32,
                                                                 max_keepalive_connections=16))
        return self._client

    def set_target(self, new_url: str) -> None:
        """Validate a new origin and invalidate pending and stored representations."""
        self.target_url = validate_target(new_url)
        self.cache.clear()
        self.telemetry.reset()

    def _key(self, request: Request, path: str, query: bytes) -> str:
        """Keep scheme, host and encoded path representations separate."""
        authority = request.scope.get("scheme", "http") + ":" + request.headers.get("host", "")
        raw_path = request.scope.get("raw_path", path.encode("utf-8")).decode("latin1")
        return self.cache.make_key("GET:" + authority, raw_path, query)

    async def handle_request(self, request: Request) -> Response:
        """Route requests and invalidate all derived reads around mutations."""
        path = request.scope.get("path", "/")
        path = path[5:] if path.startswith("/site/") else path
        query = request.scope.get("query_string", b"")
        mutation = request.method in {"POST", "PUT", "DELETE", "PATCH"}
        if mutation:
            self.cache.clear()
        try:
            if request.method == "GET" and request_cacheable(parse_headers(request.scope.get("headers", []))):
                response = self._check_cache(request, path, query)
                if response is not None:
                    return response
            async with self._requests:
                return await self._fetch_and_cache(request, path, query)
        finally:
            if mutation:
                self.cache.clear()

    def _check_cache(self, request: Request, path: str, query: bytes) -> Response | None:
        """Serve a public representation with the same validators on miss and hit."""
        cached = self.cache.get(self._key(request, path, query))
        if cached is None:
            return None
        if request.headers.get("if-none-match") == cached.etag:
            return Response(status_code=304, headers={"etag": cached.etag, "vary": "Accept-Encoding",
                                                      "cache-control": "public"})
        body, encoding = self.compressor.compress(cached.body, cached.content_type,
                                                  request.headers.get("accept-encoding", ""))
        response = Response(body, status_code=cached.status_code)
        response.raw_headers = representation_headers(cached.headers, body, cached.etag, encoding)
        self.telemetry.record_request("GET", "[redacted]", cached.status_code, 0, True,
                                     len(cached.body), len(body), encoding or "none")
        return response

    async def _fetch_and_cache(self, request: Request, path: str, query: bytes) -> Response:
        """Fetch one raw origin response with upload and buffering limits."""
        generation = self.cache.generation
        raw_path = request.scope.get("raw_path", path.encode("utf-8")).decode("ascii")
        raw_path = raw_path[5:] if raw_path.startswith("/site/") else raw_path
        url = self.target_url + raw_path + ("?" + query.decode("ascii") if query else "")
        start = time.perf_counter()
        try:
            body = await request_body(request)
            client = self.get_client()
            outgoing = client.build_request(request.method, url, headers=outgoing_headers(request), content=body)
            outgoing.headers.pop("cookie", None)
            if "cookie" in request.headers:
                outgoing.headers["cookie"] = request.headers["cookie"]
            upstream = await client.send(outgoing, stream=True)
            payload = await upstream_body(upstream)
        except BodyTooLarge:
            return Response("Request too large", status_code=413)
        except httpx.RequestError as exc:
            logger.warning("Upstream request failed (%s)", type(exc).__name__)
            return Response("Upstream server unavailable", status_code=502)
        if isinstance(payload, Response):
            return payload
        result = self._prepare_response(request, upstream, payload, (path, query, generation))
        self.telemetry.record_request(request.method, "[redacted]", upstream.status_code,
                                     (time.perf_counter() - start) * 1000, False, len(payload), len(result.body))
        return result

    def _prepare_response(self, request: Request, upstream: httpx.Response, body: bytes,
                          context: tuple[str, bytes, int]) -> Response:
        """Transform only explicitly public responses and preserve repeated headers."""
        original = filtered_headers(list(upstream.headers.raw))
        public = (request.method == "GET" and upstream.status_code == 200
                  and request_cacheable(parse_headers(request.scope.get("headers", [])))
                  and response_cacheable(parse_headers(original)))
        if public:
            content_type = upstream.headers.get("content-type", "text/plain")
            body = self.minifier.minify(body, content_type)
            path, query, generation = context
            entry = self.cache.set_if_current(generation, self._key(request, path, query),
                                               path, 200, original, body, content_type)
            body, encoding = self.compressor.compress(body, content_type, request.headers.get("accept-encoding", ""))
            original = representation_headers(original, body, entry.etag if entry else None, encoding)
        response = Response(body, status_code=upstream.status_code)
        response.raw_headers = original
        return response

    async def close(self) -> None:
        """Release upstream pooled connections on shutdown."""
        if self._client is not None:
            await self._client.aclose()
