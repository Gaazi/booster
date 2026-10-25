"""Unit tests for FastMemoryCache."""

import time
from booster.cache import FastMemoryCache


def test_cache_set_and_get() -> None:
    cache = FastMemoryCache(max_items=10, default_ttl=5.0)
    key = cache.make_key("GET", "/api/data", b"page=1")
    cache.set(key, "/api/data", 200, [], b'{"status": "ok"}', "application/json")

    entry = cache.get(key)
    assert entry is not None
    assert entry.status_code == 200
    assert entry.body == b'{"status": "ok"}'
    assert entry.etag.startswith('W/"')


def test_cache_ttl_expiration() -> None:
    cache = FastMemoryCache(max_items=10, default_ttl=0.1)
    key = cache.make_key("GET", "/api/expire")
    cache.set(key, "/api/expire", 200, [], b"temporary", "text/plain", ttl=0.05)

    time.sleep(0.1)
    assert cache.get(key) is None


def test_cache_lru_eviction() -> None:
    cache = FastMemoryCache(max_items=2, default_ttl=60.0)
    cache.set("k1", "/1", 200, [], b"1", "text/plain")
    cache.set("k2", "/2", 200, [], b"2", "text/plain")
    cache.set("k3", "/3", 200, [], b"3", "text/plain")

    assert cache.get("k1") is None
    assert cache.get("k2") is not None
    assert cache.get("k3") is not None


def test_cache_invalidation() -> None:
    cache = FastMemoryCache(max_items=10)
    k1 = cache.make_key("GET", "/posts/1")
    k2 = cache.make_key("GET", "/posts/2")
    k3 = cache.make_key("GET", "/users/1")

    cache.set(k1, "/posts/1", 200, [], b"post1")
    cache.set(k2, "/posts/2", 200, [], b"post2")
    cache.set(k3, "/users/1", 200, [], b"user1")

    removed = cache.invalidate_path_prefix("/posts")
    assert removed == 2
    assert cache.get(k1) is None
    assert cache.get(k2) is None
    assert cache.get(k3) is not None
