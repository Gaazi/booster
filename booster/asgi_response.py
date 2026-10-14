"""Optimize explicitly public ASGI responses without buffering streams."""

from typing import Any, Callable

from booster.http_policy import response_cacheable, merge_vary, is_static_asset


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

    async def __call__(self, message: dict[str, Any]) -> None:
        """Forward streams and extensions immediately, optimizing a single body."""
        if message["type"] == "http.response.start":
            self.start = dict(message)
            headers_dict = parse_headers(message.get("headers", []))
            self.cacheable = response_cacheable(headers_dict, is_static=self.is_static)
            can_opt = (self.booster.compress_dynamic and message.get("status") == 200
                       and not any(k.lower() == b"content-encoding" for k, v in message.get("headers", [])))
            self.forwarding = (message.get("status") != 200
                               or message.get("trailers", False)
                               or (not self.cacheable and not can_opt))
            if self.forwarding:
                await self.send(message)
            return
        if self.forwarding:
            await self.send(message)
            return
        if (message["type"] != "http.response.body" or message.get("more_body")
                or len(message.get("body", b"")) > 2_000_000):
            self.forwarding = True
            await self.send(self.start)
            await self.send(message)
            return
        if self.cacheable:
            await self._optimized_cacheable(message.get("body", b""))
        else:
            await self._optimized_dynamic(message.get("body", b""))

    async def _optimized_cacheable(self, raw_body: bytes) -> None:
        """Minify and compress public bytes, preserving unrelated response fields."""
        booster = self.booster
        request_headers = parse_headers(self.scope.get("headers", []))
        original = self.start.get("headers", [])
        content_type = parse_headers(original).get("content-type", "text/plain")
        body = booster.minifier.minify(raw_body, content_type) if booster.enable_minification else raw_body
        key = booster.cache_key(self.scope, request_headers)
        entry = booster.cache.set_if_current(self.generation, key, self.scope.get("path", "/"),
                                             200, original, body, content_type)
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
    headers.append((b"cdn-cache-control", b"public, max-age=300, stale-while-revalidate=60"))
    headers.append((b"surrogate-control", b"max-age=300"))
    headers.append((b"x-powered-by", b"booster"))
    return headers

