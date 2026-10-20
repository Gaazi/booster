"""Optimize explicitly public ASGI responses without buffering streams."""

from typing import Any, Callable

from booster.http_policy import (response_cacheable, request_cacheable, response_ttl,
                                 cache_directives, merge_vary, is_static_asset)
from booster.bypass import ENCODED, RESPONSE_DIRECTIVE, STATUS, STORED, STREAMED, TOO_LARGE


def parse_headers(raw: list[tuple[bytes, bytes]]) -> dict[str, str]:
    """Combine repeated fields so restrictive cache directives cannot be hidden."""
    result: dict[str, str] = {}
    for key, value in raw:
        name = key.decode("latin1").lower()
        text = value.decode("latin1")
        result[name] = result[name] + ", " + text if name in result else text
    return result


class ASGIResponseOptimizer:
    """Capture one bounded response and optimize public or dynamic representations."""

    def __init__(self, booster: Any, scope: dict[str, Any], send: Callable) -> None:
        """Keep request state separate from the shared middleware instance."""
        self.booster, self.scope, self.send = booster, scope, send
        self.start: dict[str, Any] = {}
        self.forwarding = False
        self.generation = booster.cache.generation
        self.is_static = is_static_asset(scope.get("path", "/"))
        self.cacheable = False
        self.body = bytearray()

    async def __call__(self, message: dict[str, Any]) -> None:
        """Forward streams and extensions immediately, optimizing a single body."""
        if message["type"] == "http.response.start":
            self._start_response(message)
            if self.forwarding:
                await self.send(message)
            return
        if self.forwarding:
            await self.send(message)
            return
        if not await self._collect_body(message):
            return
        if self.cacheable:
            await self._optimized_cacheable(bytes(self.body))
        else:
            await self._optimized_dynamic(bytes(self.body))

    def _start_response(self, message: dict[str, Any]) -> None:
        """Decide eligibility once using both request and response privacy rules."""
        self.start = dict(message)
        headers = parse_headers(message.get("headers", []))
        request_headers = parse_headers(self.scope.get("headers", []))
        self.request_eligible = (request_cacheable(request_headers)
                                 and not any(self.scope.get(key) for key in ("user", "auth", "session")))
        self.cacheable = (self.request_eligible
                          and response_cacheable(headers, is_static=self.is_static))
        can_opt = (self.booster.compress_dynamic and message.get("status") == 200
                   and "no-transform" not in cache_directives(headers) | cache_directives(request_headers)
                   and not any(key in headers for key in ("content-encoding", "content-range"))
                   and not any(key in request_headers for key in ("range", "if-range")))
        self.forwarding = (message.get("status") != 200 or message.get("trailers", False)
                           or (not self.cacheable and not can_opt))
        self._record_response_reason(headers)

    def _record_response_reason(self, headers: dict[str, str]) -> None:
        """Explain why an eligible request was not stored."""
        if not self.request_eligible:
            return
        if self.start.get("status") != 200:
            self.booster.bypass.record(STATUS)
        elif not self.cacheable:
            reason = ENCODED if "content-encoding" in headers else RESPONSE_DIRECTIVE
            self.booster.bypass.record(reason)

    async def _collect_body(self, message: dict[str, Any]) -> bool:
        """Buffer bounded public static files while forwarding dynamic streams promptly."""
        headers = parse_headers(self.start.get("headers", []))
        length = headers.get("content-length", "")
        bounded_static = (self.is_static and self.cacheable and length.isdigit()
                          and int(length) <= 2_000_000)
        if (message["type"] != "http.response.body"
                or (message.get("more_body") and not bounded_static)
                or len(self.body) + len(message.get("body", b"")) > 2_000_000):
            self.forwarding = True
            self._record_body_reason(message, bounded_static)
            await self.send(self.start)
            if self.body:
                await self.send({"type": "http.response.body", "body": bytes(self.body), "more_body": True})
                self.body.clear()
            await self.send(message)
            return False
        self.body.extend(message.get("body", b""))
        return not message.get("more_body", False)

    def _record_body_reason(self, message: dict[str, Any], bounded_static: bool) -> None:
        """Explain why an eligible response body was not buffered."""
        if not self.request_eligible:
            return
        if message.get("more_body") and not bounded_static:
            self.booster.bypass.record(STREAMED)
        elif len(self.body) + len(message.get("body", b"")) > 2_000_000:
            self.booster.bypass.record(TOO_LARGE)

    async def _optimized_cacheable(self, raw_body: bytes) -> None:
        """Minify and compress public bytes, preserving unrelated response fields."""
        booster = self.booster
        request_headers = parse_headers(self.scope.get("headers", []))
        original = self.start.get("headers", [])
        content_type = parse_headers(original).get("content-type", "text/plain")
        body = booster.minifier.minify(raw_body, content_type) if booster.enable_minification else raw_body
        key = booster.cache_key(self.scope, request_headers)
        entry = booster.cache.set_if_current(self.generation, key, self.scope.get("path", "/"),
                                             200, original, body, content_type,
                                             response_ttl(parse_headers(original), booster.cache.default_ttl))
        booster.bypass.record(STORED)
        encoding = None
        if booster.enable_compression:
            body, encoding = booster.compressor.compress(body, content_type,
                                                         request_headers.get("accept-encoding", ""))
        headers = representation_headers(original, body, entry.etag if entry else None, encoding)
        await self.send({**self.start, "headers": headers})
        await self.send({"type": "http.response.body", "body": body})
        booster.telemetry.record_request("GET", "[redacted]", 200, 0, False,
                                         len(raw_body), len(body), encoding or "none")

    async def _optimized_dynamic(self, raw_body: bytes) -> None:
        """Compress private dynamic bytes without storing in shared cache."""
        booster = self.booster
        request_headers = parse_headers(self.scope.get("headers", []))
        original = self.start.get("headers", [])
        content_type = parse_headers(original).get("content-type", "text/plain")
        body = booster.minifier.minify(raw_body, content_type) if booster.enable_minification else raw_body
        encoding = None
        if booster.enable_compression:
            body, encoding = booster.compressor.compress(body, content_type,
                                                         request_headers.get("accept-encoding", ""))
        headers = representation_headers(original, body, None, encoding)
        headers = [(key, value) for key, value in headers if key.lower() not in
                   {b"cdn-cache-control", b"surrogate-control"}]
        headers.extend([(b"cdn-cache-control", b"no-store"), (b"surrogate-control", b"no-store")])
        await self.send({**self.start, "headers": headers})
        await self.send({"type": "http.response.body", "body": body})
        booster.telemetry.record_request("GET", "[redacted]", 200, 0, False,
                                         len(raw_body), len(body), encoding or "none")


def representation_headers(original: list[tuple[bytes, bytes]], body: bytes,
                           etag: str | None, encoding: str | None) -> list[tuple[bytes, bytes]]:
    """Replace length, validators and negotiation fields after changing a body."""
    blocked = {b"content-length", b"content-encoding", b"etag", b"vary",
               b"content-md5", b"digest", b"content-digest", b"repr-digest"}
    headers = [(k, v) for k, v in original if k.lower() not in blocked]
    headers.append((b"content-length", str(len(body)).encode("ascii")))
    headers.append((b"vary", merge_vary(parse_headers(original).get("vary", "")).encode("latin1")))
    if etag:
        headers.append((b"etag", etag.encode("ascii")))
    if encoding:
        headers.append((b"content-encoding", encoding.encode("ascii")))
    headers.append((b"x-powered-by", b"booster"))
    return headers

