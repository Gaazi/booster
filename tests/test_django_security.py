"""Runtime Django regressions for public caching and private-response bypass."""

from __future__ import annotations
from typing import Any, Callable, AsyncIterator, Iterator

import pytest

pytest.importorskip("django")
from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse
from django.test import RequestFactory

from go_fast.django_support import DjangoRocketMiddleware

if not settings.configured:
    settings.configure(DEFAULT_CHARSET="utf-8", ALLOWED_HOSTS=["testserver"])


def test_django_public_json_length_and_headers() -> None:
    """Minified misses and hits agree on validators, lengths and safe headers."""
    calls = []
    def origin(request: Any) -> Any:
        """Return the controlled origin response for this scenario."""
        calls.append(1)
        response = HttpResponse('{ "value": 1 }', content_type="application/json")
        response["Cache-Control"] = "public"
        response["Content-Length"] = "999"
        response["X-Origin"] = "kept"
        return response
    middleware = DjangoRocketMiddleware(origin)
    factory = RequestFactory()
    first = middleware(public_request(factory, "/?q=1"))
    second = middleware(public_request(factory, "/?q=1"))
    assert first.content == second.content == b'{"value":1}'
    assert first["Content-Length"] == second["Content-Length"] == str(len(first.content))
    assert first["ETag"] == second["ETag"] and second["X-Origin"] == "kept"
    middleware(public_request(factory, "/?q=2"))
    assert len(calls) == 2


@pytest.mark.parametrize("mode", ["private", "cookie", "stream", "undeclared"])
def test_django_private_or_streaming_responses_not_cached(mode: str) -> None:
    """Cookie, private and streaming response state never enters the shared cache."""
    def origin(request: Any) -> Any:
        """Return the controlled origin response for this scenario."""
        response = StreamingHttpResponse([b"secret"]) if mode == "stream" else HttpResponse("secret")
        if mode != "undeclared":
            response["Cache-Control"] = "private" if mode == "private" else "public"
        if mode == "cookie":
            response.set_cookie("session", "secret")
        return response
    middleware = DjangoRocketMiddleware(origin)
    middleware(public_request(RequestFactory(), "/"))
    assert middleware.cache.count() == 0


def public_request(factory: Any, path: str) -> Any:
    """Omit RequestFactory's synthetic empty Cookie header for an anonymous request."""
    request = factory.get(path)
    request.META.pop("HTTP_COOKIE", None)
    return request
