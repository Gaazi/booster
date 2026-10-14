"""Integration tests for RocketBooster ASGI middleware."""

from __future__ import annotations
from typing import Any, Callable, AsyncIterator, Iterator

import pytest
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.testclient import TestClient

from booster.booster import RocketBooster


def create_test_app() -> FastAPI:
    """Verify create test app."""
    app = FastAPI()
    app.add_middleware(RocketBooster, min_compress_size=10)

    @app.get("/hello", response_class=HTMLResponse)
    def hello() -> HTMLResponse:
        """Verify hello."""
        return HTMLResponse("<html>   <body>Hello Fast World</body>   </html>", headers={"cache-control": "public"})

    @app.get("/data", response_class=JSONResponse)
    def data() -> dict:
        """Verify data."""
        return {"message": "success", "count": 100}

    @app.post("/items")
    def create_item(payload: dict) -> dict:
        """Verify create item."""
        return {"created": True}

    return app


def test_first_request_and_caching() -> None:
    """Verify first request and caching."""
    app = create_test_app()
    client = TestClient(app)

    # 1st request -> fetches, minifies, caches
    res1 = client.get("/hello")
    assert res1.status_code == 200
    assert "X-Powered-By" in res1.headers
    assert "<html>   <body>Hello Fast World</body>   </html>" in res1.text
    etag = res1.headers.get("etag")
    assert etag is not None

    # 2nd request -> served from cache
    res2 = client.get("/hello")
    assert res2.status_code == 200
    assert res2.headers.get("etag") == etag

    # 3rd request with ETag -> 304 Not Modified
    res3 = client.get("/hello", headers={"if-none-match": etag})
    assert res3.status_code == 304


def test_post_invalidation() -> None:
    """Verify post invalidation."""
    app = create_test_app()
    client = TestClient(app)

    # Prime cache
    res1 = client.get("/data")
    assert res1.status_code == 200

    # Mutate data via POST
    res_post = client.post("/items", json={"name": "new item"})
    assert res_post.status_code == 200
