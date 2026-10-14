"""Integration tests for SpeedProxyServer and dashboard endpoints."""

from __future__ import annotations
from typing import Any, Callable, AsyncIterator, Iterator

import pytest
from fastapi.testclient import TestClient
from run import app, proxy


def test_dashboard_serving() -> None:
    """Verify dashboard serving."""
    client = TestClient(app, base_url="http://127.0.0.1:5050", client=("127.0.0.1", 12345))
    res = client.get("/")
    assert res.status_code == 200
    assert "go_fast" in res.text


def test_stats_api() -> None:
    """Verify stats api."""
    client = TestClient(app, base_url="http://127.0.0.1:5050", client=("127.0.0.1", 12345))
    res = client.get("/api/stats")
    assert res.status_code == 200
    data = res.json()
    assert "total_requests" in data
    assert "hit_ratio_percent" in data
    assert "target_url" in data


def test_set_target_api() -> None:
    """Verify set target api."""
    client = TestClient(app, base_url="http://127.0.0.1:5050", client=("127.0.0.1", 12345))
    res = client.post("/api/set-target", json={"url": "http://127.0.0.1:9000"}, headers={"X-Go-Fast-Admin": "1"})
    assert res.status_code == 200
    assert proxy.target_url == "http://127.0.0.1:9000"


def test_clear_cache_api() -> None:
    """Verify clear cache api."""
    client = TestClient(app, base_url="http://127.0.0.1:5050", client=("127.0.0.1", 12345))
    res = client.post("/api/clear-cache", headers={"X-Go-Fast-Admin": "1"})
    assert res.status_code == 200
    assert res.json()["status"] == "cleared"


def test_detect_local_api() -> None:
    """Verify detect local api."""
    client = TestClient(app, base_url="http://127.0.0.1:5050", client=("127.0.0.1", 12345))
    res = client.get("/api/detect-local")
    assert res.status_code == 200
    assert "found_url" in res.json()
