"""Regression tests for privacy boundaries and bounded public caching."""

from __future__ import annotations
from typing import Any, Callable, AsyncIterator, Iterator

import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response
from starlette.testclient import TestClient

from go_fast.booster import RocketBooster
from go_fast.cache import FastMemoryCache
from go_fast.http_policy import filtered_headers, response_cacheable
from go_fast.minifier import minify_html, minify_css, minify_json
from go_fast.telemetry import TelemetryTracker
from run import app, gateway, proxy


def local_client(application: Any=app) -> Any:
    """Create a real loopback management request without trusting forwarded peers."""
    return TestClient(application, base_url="http://127.0.0.1:5050", client=("127.0.0.1", 12345))


@pytest.mark.parametrize("headers", [
    {"Origin": "https://evil.test", "X-Go-Fast-Admin": "1"},
    {"Origin": "http://127.0.0.1:5051", "X-Go-Fast-Admin": "1"},
    {"Sec-Fetch-Site": "cross-site", "X-Go-Fast-Admin": "1"},
    {"Sec-Fetch-Site": "same-site", "X-Go-Fast-Admin": "1"},
    {"Origin": "null", "X-Go-Fast-Admin": "1"}, {},
])
def test_management_write_rejects_foreign_pages(headers: Any) -> None:
    """Upstream scripts and blind HTML forms cannot change management state."""
    original = proxy.target_url
    response = local_client().post("/api/set-target", json={"url": "http://127.0.0.1:9001"}, headers=headers)
    assert response.status_code == 403
    assert proxy.target_url == original


@pytest.mark.parametrize("headers", [{"Host": "evil.test"}, {"Host": "127.0.0.1@evil.test"},
                                      {"Host": "localhost,evil.test"}, {"Origin": "null"},
                                      {"Sec-Fetch-Site": "same-site"}])
def test_management_reads_reject_foreign_requests(headers: Any) -> None:
    """Telemetry and local port discovery cannot leak to foreign browser contexts."""
    assert local_client().get("/api/stats", headers=headers).status_code == 403


def test_management_rejects_remote_peer_even_with_forwarded_headers() -> None:
    """Client identity comes from the socket rather than user-controlled headers."""
    client = TestClient(app, base_url="http://localhost:5050", client=("192.0.2.1", 1))
    assert client.get("/", headers={"X-Forwarded-For": "127.0.0.1"}).status_code == 403


def test_gateway_blocks_foreign_fetches_and_blind_writes() -> None:
    """Untrusted websites cannot use the gateway as a browser-to-intranet proxy."""
    client = local_client(gateway)
    assert client.get("/", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert client.post("/", headers={"Origin": "https://evil.test"}).status_code == 403


def test_management_same_origin_and_private_headers() -> None:
    """Normal dashboard actions work and responses cannot be cached or framed."""
    response = local_client().post("/api/clear-cache", headers={"Origin": "http://127.0.0.1:5050",
                                "Sec-Fetch-Site": "same-origin", "X-Go-Fast-Admin": "1"})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_gateway_is_separate_and_preserves_legacy_links() -> None:
    """Upstream pages have no management routes and old links change origins."""
    assert all(route.name == "proxy_gateway" for route in gateway.routes)
    response = local_client().get("/site/a%2Fb?q=2", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "http://127.0.0.1:5051/site/a%2Fb?q=2"


@pytest.mark.parametrize("url", ["http://user:pass@example.test", "http://localhost:5050",
    "http://127.0.0.2:5051", "http://[::1]:5050", "http://169.254.169.254",
    "http://[::ffff:169.254.169.254]", "http://0.0.0.0", "http://224.0.0.1",
    "http://example.test:bad", "http://example.test:65536", "http://example.test/\nsecret"])
def test_target_validation(url: str) -> None:
    """Unsafe URLs fail before mutating the configured target."""
    original = proxy.target_url
    response = local_client().post("/api/set-target", json={"url": url}, headers={"X-Go-Fast-Admin": "1"})
    assert response.status_code == 400
    assert proxy.target_url == original


@pytest.mark.parametrize("headers", [{}, {"cache-control": "private"},
    {"cache-control": "public, PRIVATE"}, {"cache-control": "public, max-age=0"},
    {"cache-control": "public", "vary": "X-User"}, {"cache-control": "public", "set-cookie": "a=b"}])
def test_only_explicitly_public_responses_cache(headers: Any) -> None:
    """Private and undeclared responses cannot be shared across users."""
    assert not response_cacheable(headers)
    assert response_cacheable({"cache-control": "PUBLIC"})


def test_private_response_is_not_transformed_or_retained() -> None:
    """Private payloads preserve validators and never enter the compression reuse cache."""
    application = FastAPI()
    calls = []
    @application.get("/")
    def private() -> Any:
        """Return a private payload with its original validator."""
        calls.append(1)
        return Response(b"secret" * 200, headers={"cache-control": "private", "etag": '"original"'})
    booster = RocketBooster(application)
    client = TestClient(booster)
    for _ in range(2):
        response = client.get("/", headers={"Accept-Encoding": "gzip"})
        assert "content-encoding" not in response.headers
        assert response.headers["etag"] == '"original"'
    assert len(calls) == 2 and booster.cache.count() == 0


def test_mutation_invalidates_other_paths() -> None:
    """A write to an item cannot leave a cached collection stale."""
    application = FastAPI()
    values = []
    @application.get("/items")
    def items() -> Any:
        """Return an explicitly public collection snapshot."""
        return Response(str(len(values)), headers={"cache-control": "public"})
    @application.post("/item")
    def add() -> Any:
        """Mutate the collection for cache invalidation verification."""
        values.append(1)
        return {}
    client = TestClient(RocketBooster(application))
    assert client.get("/items").text == "0"
    client.post("/item")
    assert client.get("/items").text == "1"


def test_cache_memory_budget_and_generation() -> None:
    """LRU eviction bounds bytes and invalidation prevents stale pending inserts."""
    cache = FastMemoryCache(max_bytes=8)
    generation = cache.generation
    cache.set("one", "/a", 200, [], b"12345")
    cache.set("two", "/b", 200, [], b"67890")
    assert cache.get("one") is None and cache.get("two") is not None
    cache.set("huge", "/c", 200, [], b"x" * 9)
    assert cache.get("huge") is None
    cache.clear()
    assert cache.set_if_current(generation, "late", "/a", 200, [], b"old") is None
    assert cache.count() == 0
    with pytest.raises(ValueError):
        FastMemoryCache(max_bytes=0)


def test_cache_keys_have_unambiguous_boundaries() -> None:
    """Path/query delimiters cannot alias another request's response."""
    cache = FastMemoryCache()
    assert cache.make_key("GET", "/a", b"b:c") != cache.make_key("GET", "/a:b", b"c")


def test_encoded_paths_and_schemes_are_separate() -> None:
    """Decoded-path aliases and HTTP/HTTPS variants cannot share representations."""
    booster = RocketBooster(None)
    scope = {"path": "/a/b", "raw_path": b"/a%2Fb", "scheme": "http"}
    first = booster.cache_key(scope, {})
    scope["raw_path"] = b"/a/b"
    assert first != booster.cache_key(scope, {})
    second = booster.cache_key(scope, {})
    scope["scheme"] = "https"
    assert second != booster.cache_key(scope, {})


def test_duplicate_cache_directives_are_combined() -> None:
    """A repeated permissive header cannot conceal a private directive."""
    async def origin(scope: dict[str, Any], receive: Callable, send: Callable) -> Any:
        """Return the controlled origin response for this scenario."""
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"cache-control", b"private"), (b"cache-control", b"public")]})
        await send({"type": "http.response.body", "body": b"secret"})
    booster = RocketBooster(origin)
    assert TestClient(booster).get("/").text == "secret"
    assert booster.cache.count() == 0


def test_asgi_extension_messages_survive() -> None:
    """File-send extensions are forwarded with their delayed response start."""
    messages = []
    async def origin(scope: dict[str, Any], receive: Callable, send: Callable) -> Any:
        """Return the controlled origin response for this scenario."""
        await send({"type": "http.response.start", "status": 200, "headers": [(b"cache-control", b"public")]})
        await send({"type": "http.response.pathsend", "path": "public.txt"})
    async def send(message: dict[str, Any]) -> None:
        """Capture an ASGI response message for assertions."""
        messages.append(message)
    asyncio.run(RocketBooster(origin)({"type": "http", "method": "GET", "path": "/"}, None, send))
    assert [m["type"] for m in messages] == ["http.response.start", "http.response.pathsend"]


def test_hop_headers_include_connection_named_fields() -> None:
    """Connection-nominated fields cannot enter end-to-end headers."""
    assert filtered_headers([(b"connection", b"X-Secret"), (b"x-secret", b"hidden"),
                             (b"x-kept", b"ok")]) == [(b"x-kept", b"ok")]


def test_minification_preserves_source_semantics() -> None:
    """Inline spacing, selectors, placeholder-like text and JSON precision survive."""
    html = '<span>a</span> <span title="<!-- keep -->">b</span><go-fast-protected-0><script>safe()</script>'
    css = 'a :hover { --gap:  ; content: "GOFASTSTRING0TOKEN"; }'
    assert minify_html(html) == html
    assert minify_css(css) == css
    assert minify_json('{ "value": 0.123456789012345678901, "x": "a b" }') == '{"value":0.123456789012345678901,"x":"a b"}'


def test_telemetry_is_thread_safe_and_redacts_paths() -> None:
    """Concurrent counters remain accurate and logs contain no URL tokens."""
    tracker = TelemetryTracker()
    def record(_: Any) -> None:
        """Record one redacted request for concurrent counter verification."""
        tracker.record_request("GET", "/reset/secret-token", 200, 1, False, 1, 1)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(record, range(2000)))
    stats = tracker.get_stats()
    assert stats["total_requests"] == 2000
    assert all(log["path"] == "[redacted]" for log in stats["recent_logs"])
    stats["recent_logs"][0]["path"] = "changed"
    assert tracker.get_stats()["recent_logs"][0]["path"] == "[redacted]"
