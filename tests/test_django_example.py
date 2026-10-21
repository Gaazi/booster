"""Verify the Django example host behaves like the documented recipe."""

from typing import Any

import pytest

pytest.importorskip("django")

from django.conf import settings

if not settings.configured:
    settings.configure(DEFAULT_CHARSET="utf-8", ALLOWED_HOSTS=["testserver"])

from django.test import RequestFactory

from examples.django_host import account, build_middleware, public_asset


def anonymous_request(factory: Any, path: str) -> Any:
    """Return a request without RequestFactory's synthetic empty cookie."""
    request = factory.get(path)
    request.META.pop("HTTP_COOKIE", None)
    return request


def test_public_view_is_cached_and_private_view_is_not() -> None:
    """Only the view that declares a public policy may enter the cache."""
    calls: list[str] = []

    def origin(request: Any) -> Any:
        """Serve the example views and count the origin calls."""
        calls.append(request.path)
        return public_asset(request) if request.path == "/static/app.css" else account(request)

    middleware = build_middleware(origin)
    factory = RequestFactory()
    first = middleware(anonymous_request(factory, "/static/app.css"))
    second = middleware(anonymous_request(factory, "/static/app.css"))
    assert first.content == second.content == b"body{color:red}"
    assert calls == ["/static/app.css"], "the second public request must be served from the cache"

    middleware(anonymous_request(factory, "/account"))
    middleware(anonymous_request(factory, "/account"))
    assert calls.count("/account") == 2, "a private response must reach the view every time"


def test_example_settings_use_the_booster_middleware() -> None:
    """The example must register Booster in the documented position."""
    from examples.django_host import MIDDLEWARE

    assert MIDDLEWARE[0] == "booster.DjangoRocketMiddleware"
