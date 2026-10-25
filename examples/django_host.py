"""Example Django host showing how a project embeds Booster as middleware.

Django middleware has no route policy, so a Django site opts in per response:
only views that declare `Cache-Control: public` can enter the shared cache.
Everything else, including every personalized page, stays untouched.
"""

from typing import Any, Callable

from django.http import HttpRequest, HttpResponse

SECRET_KEY = "example-only-not-a-real-secret"
ALLOWED_HOSTS = ["*"]

MIDDLEWARE = [
    "booster.DjangoRocketMiddleware",
    "django.middleware.security.SecurityMiddleware",
]


def public_asset(request: HttpRequest) -> HttpResponse:
    """Serve a public asset that declares its own cache policy."""
    response = HttpResponse("body{color:red}", content_type="text/css")
    response["Cache-Control"] = "public, max-age=300"
    return response


def account(request: HttpRequest) -> HttpResponse:
    """Serve a personalized page that must never enter the shared cache."""
    response = HttpResponse("user:abc", content_type="text/plain")
    response["Cache-Control"] = "private, no-store"
    return response


def build_middleware(get_response: Callable[[HttpRequest], HttpResponse]) -> Any:
    """Create the Booster middleware for this example site."""
    from booster.django_support import DjangoRocketMiddleware

    return DjangoRocketMiddleware(get_response)
