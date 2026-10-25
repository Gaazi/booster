"""Focused regressions for the October host integration and worker changes."""

import asyncio
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest

from booster import FileInvalidationBus, RocketBooster
from booster.invalidation import LocalInvalidationBus
from booster.initializer import render_adapter, write_adapter
from booster.site_config import SiteConfig
from test_origin_age import build_scope, call, origin


def test_explicit_local_bus_can_serve_requests() -> None:
    """The exported process-local bus must implement the iterable drain contract."""
    engine = RocketBooster(origin(), invalidation_bus=LocalInvalidationBus())
    body, _ = asyncio.run(call(engine, build_scope("/static/app.css")))
    assert body == b"body{}"


def test_file_bus_rotation_is_detected_after_it_refills(tmp_path: Path) -> None:
    """A slow reader must detect a rotation even after the file grows again."""
    path = tmp_path / "notices.log"
    publisher = FileInvalidationBus(path, max_bytes=128)
    reader = FileInvalidationBus(path, max_bytes=128)
    publisher.publish("/a")
    reader.drain()
    publisher.publish("/rotate" * 30)
    publisher.publish("/unrelated" * 4)
    assert "*" in reader.drain()


def test_generated_adapter_honors_the_configured_bus(tmp_path: Path) -> None:
    """The normal scaffolded host adapter must pass shared invalidation through."""
    from starlette.applications import Starlette

    config = tmp_path / "booster.json"
    config.write_text(json.dumps({"invalidation_file": str(tmp_path / "notices.log")}), encoding="utf-8")
    adapter = write_adapter(tmp_path, ("/static/",), ())
    namespace: dict[str, Any] = {"__file__": str(adapter)}
    exec(compile(adapter.read_text(encoding="utf-8"), str(adapter), "exec"), namespace)
    engine = namespace["attach_booster"](Starlette())
    assert engine is not None
    assert engine.get_status()["configuration"]["invalidation"] == "shared"


@pytest.mark.parametrize("setting", ["enable_compression", "enable_minification", "surgical_invalidation"])
def test_configuration_rejects_string_booleans(setting: str) -> None:
    """A string false must never silently enable transformations or narrow clears."""
    with pytest.raises(ValueError):
        SiteConfig.from_dict({setting: "false"})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_configuration_rejects_nonfinite_limits(value: float) -> None:
    """Nonfinite JSON numbers must not bypass TTL or cache memory limits."""
    with pytest.raises(ValueError):
        SiteConfig.from_dict({"cache_ttl": value})


def test_configuration_rejects_fractional_byte_budget() -> None:
    """A sub-byte budget must not become zero after validation."""
    with pytest.raises(ValueError):
        SiteConfig.from_dict({"max_cache_bytes": 0.5})


def test_adapter_quotes_route_prefixes_as_data() -> None:
    """Quotes and backslashes inside route prefixes must not break generated code."""
    source = render_adapter(('/static/a"b\\c/',), ())
    compile(source, "booster_plugin.py", "exec")


@pytest.mark.parametrize("age", ["invalid", "NaN", "Infinity", "-1", "1.5", "5, 6"])
def test_invalid_origin_age_never_enters_ram(age: str) -> None:
    """Malformed upstream age values must fail closed without poisoning hits."""
    engine = RocketBooster(origin(age=age))
    asyncio.run(call(engine, build_scope("/static/app.css")))
    assert engine.cache.count() == 0


def test_cached_asset_emits_one_updated_age_header() -> None:
    """RAM hits and conditional responses must replace the original Age field."""
    engine = RocketBooster(origin())
    _, first = asyncio.run(call(engine, build_scope("/static/app.css")))
    _, hit = asyncio.run(call(engine, build_scope("/static/app.css")))
    assert len([value for name, value in hit if name.lower() == b"age"]) == 1
    conditional = build_scope("/static/app.css")
    conditional["headers"].append((b"if-none-match", dict(first)[b"etag"]))
    _, headers = asyncio.run(call(engine, conditional))
    assert len([value for name, value in headers if name.lower() == b"age"]) == 1


@pytest.mark.skipif(shutil.which("node") is None, reason="Cross-runtime gate needs Node")
def test_python_and_node_publish_without_losing_notices(tmp_path: Path) -> None:
    """Concurrent publishers in both runtimes must retain every complete notice."""
    path = tmp_path / "notices.log"
    publisher, reader = FileInvalidationBus(path), FileInvalidationBus(path)
    peer = Path(__file__).resolve().parents[1] / "booster-node/test/bus-peer.ts"
    child = subprocess.Popen(["node", str(peer), str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for index in range(40):
            publisher.publish(f"/python/{index}")
        _, errors = child.communicate(timeout=20)
        assert child.returncode == 0, errors.decode("utf-8", errors="replace")
        notices = reader.drain()
        assert len(notices) == 80
        assert set(notices) == {f"/{runtime}/{index}" for runtime in ("python", "node") for index in range(40)}
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate()


def test_bus_round_trips_prefixes_with_newlines_and_unicode(tmp_path: Path) -> None:
    """A decoded URL path must stay one notice rather than injecting log lines."""
    publisher = FileInvalidationBus(tmp_path / "notices.log")
    reader = FileInvalidationBus(tmp_path / "notices.log")
    publisher.publish("/a\n\u03b1")
    assert reader.drain() == ["/a\n\u03b1"]


def test_django_cache_hits_advance_the_origin_age(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Django adapter must use the same resident-age calculation as ASGI."""
    from django.http import HttpResponse
    from django.test import RequestFactory
    from test_django_example import anonymous_request
    from booster.django_support import DjangoRocketMiddleware

    def aged_asset(request: Any) -> HttpResponse:
        """Return an upstream-aged public asset."""
        return HttpResponse(b"body{}", headers={"Age": "12", "Cache-Control": "public, max-age=60"})

    engine = DjangoRocketMiddleware(aged_asset)
    request = anonymous_request(RequestFactory(), "/static/app.css")
    engine(request)
    later = time.monotonic() + 10
    monkeypatch.setattr("booster.http_policy.time.monotonic", lambda: later)
    assert int(engine(request)["Age"]) >= 22
