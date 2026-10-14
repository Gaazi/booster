"""Django middleware support for go_fast RocketBooster."""

import time
from typing import Any, Callable

from go_fast.cache import FastMemoryCache
from go_fast.compressor import ResponseCompressor
from go_fast.minifier import FastMinifier
from go_fast.telemetry import TelemetryTracker


class DjangoRocketMiddleware:
    """WSGI-compatible Django middleware providing caching and compression."""

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response
        self.cache = FastMemoryCache(max_items=1000, default_ttl=300.0)
        self.compressor = ResponseCompressor()
        self.minifier = FastMinifier()
        self.telemetry = TelemetryTracker()

    def __call__(self, request: Any) -> Any:
        """Process incoming Django request with caching and compression."""
        method = getattr(request, "method", "GET").upper()
        path = getattr(request, "path", "/")

        if method in ("POST", "PUT", "DELETE", "PATCH"):
            self.cache.invalidate_path_prefix(path)
            return self.get_response(request)

        if method == "GET":
            query = getattr(request, "META", {}).get("QUERY_STRING", "").encode("latin1")
            cache_key = self.cache.make_key("GET", path, query)
            cached = self.cache.get(cache_key)
            if cached:
                from django.http import HttpResponse  # type: ignore
                response = HttpResponse(cached.body, status=cached.status_code, content_type=cached.content_type)
                response["ETag"] = cached.etag
                response["X-Powered-By"] = "go_fast RocketBooster"
                return response

        start_time = time.perf_counter()
        response = self.get_response(request)
        duration = (time.perf_counter() - start_time) * 1000

        content_type = response.get("Content-Type", "text/html")
        if response.status_code == 200 and method == "GET" and hasattr(response, "content"):
            minified = self.minifier.minify(response.content, content_type)
            key = self.cache.make_key("GET", path)
            self.cache.set(key, path, 200, [], minified, content_type)
            response.content = minified
            response["X-Powered-By"] = "go_fast RocketBooster"

        return response
