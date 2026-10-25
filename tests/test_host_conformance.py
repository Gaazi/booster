"""Run the documented conformance checklist against the example host application."""

from examples.host_app import app, engine, request

PUBLIC_PATH = "/static/app.v1.css"
PRIVATE_PATH = "/account"
MUTATION_PATH = "/catalog"
SECURITY_HEADER = b"x-frame-options"


def hits() -> int:
    """Read the engine cache-hit counter."""
    return engine.get_status()["metrics"]["cache_hits"]


def test_public_route_is_served_from_cache() -> None:
    """A repeated public request must be answered from the cache."""
    first = request("GET", PUBLIC_PATH)
    before = hits()
    second = request("GET", PUBLIC_PATH)
    assert first[0] == second[0] == 200
    assert first[1] == second[1]
    assert hits() == before + 1, "second request was not served from the cache"


def test_credentialed_request_never_uses_the_cache() -> None:
    """A cookie-bearing request must always reach the application."""
    request("GET", PUBLIC_PATH)
    before = hits()
    status, _, _ = request("GET", PUBLIC_PATH, {"cookie": "session=abc"})
    assert status == 200
    assert hits() == before, "a credentialed request was served from the cache"


def test_private_route_is_not_stored() -> None:
    """A personalized response must never come from the shared cache."""
    before = hits()
    request("GET", PRIVATE_PATH, {"cookie": "session=abc"})
    request("GET", PRIVATE_PATH, {"cookie": "session=abc"})
    assert hits() == before, "a personalized response was served from the cache"


def test_mutation_invalidates_the_cache() -> None:
    """A write must invalidate the cached read of the same route."""
    request("GET", PUBLIC_PATH)
    request("POST", MUTATION_PATH)
    before = hits()
    request("GET", PUBLIC_PATH)
    assert hits() == before, "the cached entry survived a write"


def test_security_headers_survive_a_cache_hit() -> None:
    """Outer security middleware must still decorate a cached response."""
    request("GET", PUBLIC_PATH)
    status, _, headers = request("GET", PUBLIC_PATH)
    assert status == 200
    assert any(name.lower() == SECURITY_HEADER for name, _ in headers), \
        "security headers are missing on a cache hit"
