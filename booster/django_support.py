"""Django public-response caching with privacy and content-length safeguards."""

from typing import Any, Callable

from booster.http_policy import request_cacheable, response_cacheable, response_ttl, is_static_asset
from booster.cache import FastMemoryCache
from booster.compressor import ResponseCompressor
from booster.minifier import FastMinifier
from booster.telemetry import TelemetryTracker


class DjangoRocketMiddleware:
    """Cache only explicitly public, bounded and non-streaming Django responses."""

    def __init__(self, get_response: Callable) -> None:
        """Initialize the downstream callable and bounded optimization services."""
        self.get_response = get_response
        self.cache = FastMemoryCache(max_items=1000, default_ttl=300.0)
        self.compressor = ResponseCompressor()
        self.minifier = FastMinifier()
        self.telemetry = TelemetryTracker()

    def __call__(self, request: Any) -> Any:
        """Bypass personalized requests and invalidate derived reads around writes."""
        method = request.method.upper()
        if method in {"POST", "PUT", "DELETE", "PATCH"}:
            self.cache.clear()
            try:
                return self.get_response(request)
            finally:
                self.cache.clear()
        headers = {k.lower(): v for k, v in request.headers.items()}
        is_static = is_static_asset(request.path)
        if (method != "GET" or not request_cacheable(headers)
                or getattr(getattr(request, "user", None), "is_authenticated", False)):
            return self.get_response(request)
        query = request.META.get("QUERY_STRING", "").encode("latin1")
        key = self.cache.make_key("GET:" + request.scheme + ":" + headers.get("host", ""), request.path, query)
        cached = self.cache.get(key)
        if cached:
            return self._cached_response(cached)
        generation = self.cache.generation
        response = self.get_response(request)
        return self._store_response(request.path, key, response, generation, is_static=is_static)

    def _cached_response(self, cached: Any) -> Any:
        """Restore headers with a length matching the cached representation."""
        from django.http import HttpResponse
        response = HttpResponse(cached.body, status=cached.status_code, content_type=cached.content_type)
        for name, value in cached.headers:
            if name.lower() not in {b"content-length", b"etag", b"content-md5", b"digest", b"content-digest", b"repr-digest"}:
                response[name.decode("latin1")] = value.decode("latin1")
        response["Content-Length"] = str(len(cached.body))
        response["ETag"] = cached.etag
        return response

    def _store_response(self, path: str, key: str, response: Any, generation: int,
                        is_static: bool = False) -> Any:
        """Cache only a public response and correct validators after minification."""
        headers = {k.lower(): v for k, v in response.items()}
        if (response.status_code != 200 or response.streaming or response.cookies
                or not response_cacheable(headers, is_static=is_static) or len(response.content) > 2_000_000):
            return response
        content_type = response.get("Content-Type", "text/html")
        response.content = self.minifier.minify(response.content, content_type)
        for name in ("ETag", "Content-MD5", "Digest", "Content-Digest", "Repr-Digest"):
            if response.has_header(name):
                del response[name]
        response["Content-Length"] = str(len(response.content))
        entry = self.cache.set_if_current(generation, key, path, 200,
                                          [(k.encode("latin1"), v.encode("latin1")) for k, v in response.items()],
                                          response.content, content_type,
                                          response_ttl(headers, self.cache.default_ttl))
        if entry:
            response["ETag"] = entry.etag
        return response
