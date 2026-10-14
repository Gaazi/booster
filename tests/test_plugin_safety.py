"""Regression coverage for reusable route policy and shared-cache boundaries."""

import gzip
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.responses import Response
from starlette.requests import Request
from starlette.testclient import TestClient

import booster


def public_fixture(**options):
    """Expose one public asset and a call counter through the real middleware."""
    app = FastAPI()
    calls = []

    @app.get("/static/file.css")
    def asset(request: Request) -> Response:
        """Echo credentials so accidental sharing is observable."""
        calls.append(1)
        identity = request.headers.get("cookie") or request.headers.get("authorization") or "public"
        return Response(identity, media_type="text/css", headers={"cache-control": "public, max-age=60"})

    engine = booster.attach(app, **options)
    return TestClient(app), engine, calls


@pytest.mark.parametrize("headers", [{"cookie": "alice"}, {"authorization": "alice"},
    {"range": "bytes=0-3"}, {"if-range": '"old"'}, {"cache-control": "no-cache"}])
def test_static_cache_checks_request_before_lookup(headers):
    """A warm static cache never bypasses credentials, ranges or revalidation."""
    client, engine, calls = public_fixture()
    assert client.get("/static/file.css").text == "public"
    client.get("/static/file.css", headers=headers)
    assert len(calls) == 2
    assert client.get("/static/file.css").text == "public"
    assert len(calls) == 2 and engine.cache.count() == 1


def test_dynamic_credentials_cannot_populate_public_cache():
    """Dynamic optimization cannot promote an authenticated public-looking response."""
    client, engine, calls = public_fixture(compress_dynamic=True)
    assert client.get("/static/file.css", headers={"cookie": "alice"}).text == "alice"
    assert client.get("/static/file.css").text == "public"
    assert len(calls) == 2 and engine.cache.count() == 1


@pytest.mark.parametrize("control", ["", "private", "public, no-cache", "public, no-transform",
    "public, max-age=0", "public, max-age=invalid", "public, s-maxage=0"])
def test_static_suffix_does_not_override_response_policy(control):
    """A file-like URL alone never authorizes storing a response."""
    app = FastAPI()

    @app.get("/secret.css")
    def secret() -> Response:
        """Return content with the selected origin cache policy."""
        return Response("secret", headers={"cache-control": control})

    engine = booster.attach(app)
    client = TestClient(app)
    client.get("/secret.css")
    client.get("/secret.css")
    assert engine.cache.count() == 0


def test_static_ttl_respects_origin_freshness():
    """A plugin default cannot extend a shorter origin lifetime."""
    client, engine, _ = public_fixture(cache_ttl=300)
    client.get("/static/file.css")
    scope = {"scheme": "http", "path": "/static/file.css", "query_string": b""}
    entry = engine.cache.get(engine.cache_key(scope, {"host": "testserver"}))
    assert entry.ttl == 60


def test_private_compression_has_no_public_edge_cache_policy():
    """Private dynamic bytes remain excluded from both RAM and CDN caching."""
    app = FastAPI()

    @app.get("/private")
    def private() -> Response:
        """Return a compressible private response."""
        return Response("secret " * 1000, media_type="text/plain", headers={"cache-control": "private, no-store"})

    engine = booster.attach(app, compress_dynamic=True)
    response = TestClient(app).get("/private", headers={"accept-encoding": "gzip"})
    assert response.headers["content-encoding"] == "gzip"
    assert response.headers.get("cdn-cache-control", "no-store") == "no-store"
    assert response.headers.get("surrogate-control", "no-store") == "no-store"
    assert engine.cache.count() == 0


def test_preencoded_asset_is_preserved():
    """Already compressed bytes retain their encoding and original validators."""
    app = FastAPI()
    payload = gzip.compress(b"body {color: red;}" * 100)

    @app.get("/encoded.css")
    def encoded() -> Response:
        """Return one origin-compressed asset."""
        return Response(payload, media_type="text/css", headers={"cache-control": "public",
                        "content-encoding": "gzip", "etag": '"original"'})

    engine = booster.attach(app)
    response = TestClient(app).get("/encoded.css")
    assert response.content == gzip.decompress(payload)
    assert response.headers["etag"] == '"original"' and engine.cache.count() == 0


def test_route_policy_boundaries_and_exclusions():
    """Explicit subtrees are allowed while private exclusions take precedence."""
    policy = booster.CachePolicy(("/static/", "/public"), ("/static/uploads/",))
    assert policy.allows("/static/app.css") and policy.allows("/public")
    assert not policy.allows("/static/uploads/a.css")
    assert not policy.allows("/public-private") and not policy.allows("/private")
    client, engine, calls = public_fixture(cache_policy=booster.CachePolicy(()))
    client.get("/static/file.css")
    client.get("/static/file.css")
    assert len(calls) == 2 and engine.cache.count() == 0


@pytest.mark.parametrize("paths", [("relative",), "/static/", (1,)])
def test_invalid_route_configuration_fails_early(paths):
    """Reject configuration mistakes instead of silently broadening caching."""
    with pytest.raises(ValueError):
        booster.CachePolicy(paths)


def test_only_one_package_and_command_are_shipped():
    """Package metadata exposes only the canonical Booster implementation."""
    import tomllib
    from pathlib import Path
    config = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text())
    assert config["tool"]["setuptools"]["packages"]["find"]["include"] == ["booster*"]
    assert config["project"]["scripts"] == {"booster": "booster.server:main"}


def test_duplicate_attachment_fails_before_serving():
    """Avoid accidental double caching or compression middleware."""
    app = FastAPI()
    booster.attach(app)
    with pytest.raises(ValueError, match="already attached"):
        booster.attach(app)


def test_large_static_file_is_buffered_once(tmp_path):
    """A bounded FileResponse split into chunks is served from RAM on the next read."""
    from starlette.staticfiles import StaticFiles
    data = b"font bytes " * 20000
    (tmp_path / "font.woff2").write_bytes(data)

    class PublicFiles(StaticFiles):
        """Declare public cache intent at the source."""

        async def get_response(self, path, scope):
            """Mark successful files explicitly public before Booster sees them."""
            response = await super().get_response(path, scope)
            response.headers["cache-control"] = "public, max-age=60"
            return response

    app = FastAPI()
    engine = booster.attach(app, enable_minification=False)
    files = PublicFiles(directory=tmp_path)
    app.mount("/static", files)
    with patch.object(files, "get_response", wraps=files.get_response) as origin:
        client = TestClient(app)
        assert client.get("/static/font.woff2").content == data
        assert client.get("/static/font.woff2").content == data
        assert origin.call_count == 1 and engine.cache.count() == 1
