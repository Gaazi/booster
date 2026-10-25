"""Verify the shared, framework-neutral API for private host dashboards."""

from booster import RocketBooster


def test_status_excludes_private_cache_keys_and_logs() -> None:
    """Dashboard summaries expose counters without retaining request identities."""
    engine = RocketBooster(None, max_cache_items=10)
    engine.cache.set("private-token", "/private-token", 200, [], b"private-content")
    engine.telemetry.record_request("GET", "/guest-secret", 200, 1, True, 15, 15)
    status = engine.get_status()
    assert status["cache"]["items"] == 1 and status["cache"]["bytes"] == 15
    assert status["cache"]["max_items"] == 10
    assert status["metrics"]["cache_hits"] == 1
    assert "recent_logs" not in status["metrics"]
    assert "private-token" not in str(status) and "private-content" not in str(status)
    assert "guest-secret" not in str(status)


def test_clear_cache_preserves_lifetime_metrics() -> None:
    """Clearing assets changes resident counters while retaining the request history."""
    engine = RocketBooster(None)
    engine.cache.set("one", "/one", 200, [], b"data")
    engine.telemetry.record_request("GET", "/one", 200, 1, False, 4, 4)
    engine.cache.clear()
    status = engine.get_status()
    assert status["cache"]["items"] == 0 and status["cache"]["bytes"] == 0
    assert status["metrics"]["total_requests"] == 1


def test_host_can_limit_cache_memory() -> None:
    """A small website can bound RAM without reimplementing the cache."""
    engine = RocketBooster(None, max_cache_bytes=8)
    engine.cache.set("too-large", "/static/large", 200, [], b"x" * 9)
    status = engine.get_status()
    assert status["cache"]["items"] == 0 and status["cache"]["max_bytes"] == 8


def test_invalid_memory_budget_fails_at_attachment() -> None:
    """An invalid byte cap cannot leave the website with an unbounded cache."""
    import pytest
    with pytest.raises(ValueError, match="max_bytes"):
        RocketBooster(None, max_cache_bytes=0)
