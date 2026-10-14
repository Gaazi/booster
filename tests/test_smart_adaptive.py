"""Tests for Universal Smart Adaptive Booster capabilities."""

from __future__ import annotations
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, Response
from starlette.requests import Request
from starlette.testclient import TestClient

from go_fast.booster import RocketBooster
from go_fast.http_policy import is_static_asset


def test_is_static_asset_detection() -> None:
    """Verify static asset path identification."""
    assert is_static_asset("/static/css/theme.css") is True
    assert is_static_asset("/assets/bundle.js") is True
    assert is_static_asset("/fonts/inter.woff2") is True
    assert is_static_asset("/images/logo.png") is True
    assert is_static_asset("/favicon.ico") is True
    assert is_static_asset("/i/wedding-card") is False
    assert is_static_asset("/dashboard") is False
    assert is_static_asset("/") is False


def test_static_asset_turbo_cached_with_cookies() -> None:
    """Static assets should be cached and served from RAM even if client sends cookies."""
    app = FastAPI()
    booster = RocketBooster(app)
    calls = []

    @app.get("/static/app.css")
    def get_css() -> Response:
        calls.append(1)
        return Response("body { color: red; }", media_type="text/css",
                        headers={"cache-control": "public, max-age=31536000"})

    client = TestClient(booster)

    # First request primes cache
    res1 = client.get("/static/app.css", headers={"cookie": "session=xyz123"})
    assert res1.status_code == 200
    assert len(calls) == 1

    # Second request with different cookie hits RAM cache directly
    res2 = client.get("/static/app.css", headers={"cookie": "session=abc999"})
    assert res2.status_code == 200
    assert len(calls) == 1  # Origin was not called again!

    # Third request with matching ETag returns 304
    etag = res2.headers.get("etag")
    assert etag is not None
    res3 = client.get("/static/app.css", headers={"if-none-match": etag})
    assert res3.status_code == 304


def test_private_routes_never_leak_in_shared_cache() -> None:
    """Personalized / private routes must never be stored in the shared cache."""
    app = FastAPI()
    booster = RocketBooster(app)
    users = {"user1": "Card for Alice", "user2": "Card for Bob"}

    @app.get("/i/card")
    def get_card(request: Request) -> Response:
        cookie_val = request.headers.get("cookie", "")
        return Response(users.get(cookie_val, "Default Card"), media_type="text/html",
                        headers={"cache-control": "private, no-cache, no-store"})

    client = TestClient(booster)

    res_alice = client.get("/i/card", headers={"cookie": "user1"})
    assert res_alice.text == "Card for Alice"

    res_bob = client.get("/i/card", headers={"cookie": "user2"})
    assert res_bob.text == "Card for Bob"  # NEVER gets Alice's cached card!


def test_dynamic_compression_when_enabled() -> None:
    """When compress_dynamic=True, private responses are compressed on the fly."""
    app = FastAPI()
    booster = RocketBooster(app, compress_dynamic=True, min_compress_size=10)

    @app.get("/i/large-card")
    def get_card() -> Response:
        return Response("<html><body>" + ("Hello World " * 100) + "</body></html>",
                        media_type="text/html",
                        headers={"cache-control": "private, no-cache, no-store"})

    client = TestClient(booster)

    res = client.get("/i/large-card", headers={"accept-encoding": "gzip"})
    assert res.status_code == 200
    assert res.headers.get("content-encoding") == "gzip"
    assert "private" in res.headers.get("cache-control", "")
