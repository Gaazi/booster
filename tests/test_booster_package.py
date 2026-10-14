"""Tests verifying that booster package exports match go_fast and work identically."""

from __future__ import annotations
import inspect
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from starlette.testclient import TestClient

import booster
import go_fast


def test_top_level_exports_parity() -> None:
    """Verify that booster and go_fast expose identical public symbols."""
    expected_exports = {
        "RocketBooster",
        "FastMemoryCache",
        "ResponseCompressor",
        "FastMinifier",
        "SpeedProxyServer",
        "DjangoRocketMiddleware",
        "TelemetryTracker",
        "attach",
    }
    for name in expected_exports:
        assert hasattr(booster, name), f"booster missing {name}"
        assert hasattr(go_fast, name), f"go_fast missing {name}"
    assert booster.attach == booster.RocketBooster.attach
    assert go_fast.attach == go_fast.RocketBooster.attach


def test_booster_attach_helper() -> None:
    """Verify booster.attach registers middleware and caches public responses."""
    app = FastAPI()
    attached = booster.attach(app, min_compress_size=5)

    @app.get("/booster-hello", response_class=HTMLResponse)
    def hello() -> HTMLResponse:
        return HTMLResponse("<h1>Booster Live</h1>", headers={"cache-control": "public"})

    client = TestClient(app)
    res1 = client.get("/booster-hello")
    assert res1.status_code == 200
    assert "x-powered-by" in res1.headers
    assert "booster" in res1.headers["x-powered-by"]
    assert attached.cache.count() == 1


    etag = res1.headers.get("etag")
    assert etag is not None
    res2 = client.get("/booster-hello", headers={"if-none-match": etag})
    assert res2.status_code == 304


def test_booster_submodule_structure() -> None:
    """Verify essential booster submodules and classes instantiate properly."""
    cache = booster.FastMemoryCache(max_items=10)
    compressor = booster.ResponseCompressor(min_size=10)
    minifier = booster.FastMinifier()
    telemetry = booster.TelemetryTracker()

    assert cache.count() == 0
    assert compressor.min_size == 10
    assert telemetry.get_stats()["total_requests"] == 0
    assert minifier.minify("<html> <body> test </body> </html>", "text/html") is not None
