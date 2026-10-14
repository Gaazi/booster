"""Integration tests for SpeedProxyServer and dashboard endpoints."""

import pytest
from fastapi.testclient import TestClient
from run import app, proxy


def test_dashboard_serving() -> None:
    client = TestClient(app)
    res = client.get("/")
    assert res.status_code == 200
    assert "go_fast" in res.text


def test_stats_api() -> None:
    client = TestClient(app)
    res = client.get("/api/stats")
    assert res.status_code == 200
    data = res.json()
    assert "total_requests" in data
    assert "hit_ratio_percent" in data
    assert "target_url" in data


def test_set_target_api() -> None:
    client = TestClient(app)
    res = client.post("/api/set-target", json={"url": "http://127.0.0.1:9000"})
    assert res.status_code == 200
    assert proxy.target_url == "http://127.0.0.1:9000"


def test_clear_cache_api() -> None:
    client = TestClient(app)
    res = client.post("/api/clear-cache")
    assert res.status_code == 200
    assert res.json()["status"] == "cleared"


def test_detect_local_api() -> None:
    client = TestClient(app)
    res = client.get("/api/detect-local")
    assert res.status_code == 200
    assert "found_url" in res.json()
