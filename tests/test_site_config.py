"""Verify the declarative site configuration."""

import json
from pathlib import Path
from typing import Any

import pytest

from booster.cache_policy import CachePolicy
from booster.site_config import SiteConfig, attach_from_config

SITE = {
    "include_paths": ["/static/css/", "/static/js/"],
    "exclude_paths": ["/media/", "/api/"],
    "cache_ttl": 120,
    "max_cache_bytes": 8388608,
    "enable_compression": False,
    "enable_minification": False,
    "invalidation_file": None,
}


def test_configuration_builds_the_route_policy() -> None:
    """The declared prefixes must become the route policy."""
    config = SiteConfig.from_dict(SITE)
    policy = config.cache_policy()
    assert isinstance(policy, CachePolicy)
    assert policy.include_paths == ("/static/css/", "/static/js/")
    assert policy.exclude_paths == ("/media/", "/api/")
    assert policy.allows("/static/css/main.css") is True
    assert policy.allows("/media/photo.png") is False


def test_configuration_builds_the_attach_options() -> None:
    """The declared limits must reach the engine attach call."""
    options = SiteConfig.from_dict(SITE).attach_options()
    assert options["cache_ttl"] == 120
    assert options["max_cache_bytes"] == 8388608
    assert options["enable_compression"] is False
    assert options["enable_minification"] is False
    assert options["surgical_invalidation"] is False


def test_unknown_key_is_rejected() -> None:
    """An unknown setting must fail fast instead of being ignored."""
    with pytest.raises(ValueError, match="Unknown site configuration keys"):
        SiteConfig.from_dict({"include_paths": ["/static/"], "turbo": True})


def test_invalid_values_are_rejected() -> None:
    """Invalid prefixes and limits must fail fast."""
    with pytest.raises(ValueError):
        SiteConfig.from_dict({"include_paths": "static/"})
    with pytest.raises(ValueError):
        SiteConfig.from_dict({"exclude_paths": ["media/"]})
    with pytest.raises(ValueError):
        SiteConfig.from_dict({"cache_ttl": 0})
    with pytest.raises(ValueError):
        SiteConfig.from_dict({"max_cache_bytes": -1})


def test_configuration_is_read_from_a_json_file(tmp_path: Path) -> None:
    """The configuration must load from one JSON file."""
    path = tmp_path / "booster.json"
    path.write_text(json.dumps(SITE), encoding="utf-8")
    config = SiteConfig.from_file(path)
    assert config.include_paths == ("/static/css/", "/static/js/")
    assert config.cache_ttl == 120


def test_attach_from_config_uses_the_declared_policy() -> None:
    """The engine must apply the declared policy when it is attached."""
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route

    async def asset(request: Any) -> PlainTextResponse:
        """Serve a public asset."""
        return PlainTextResponse("body{}", headers={"Cache-Control": "public, max-age=60"})

    async def account(request: Any) -> PlainTextResponse:
        """Serve a personalized page."""
        return PlainTextResponse("user:abc", headers={"Cache-Control": "private, no-store"})

    app = Starlette(routes=[Route("/static/css/main.css", asset), Route("/account", account)])
    engine = attach_from_config(app, SiteConfig.from_dict(SITE))
    assert engine.cache_policy.include_paths == ("/static/css/", "/static/js/")
    assert engine.cache_policy.allows("/account") is False


def test_invalidation_file_is_optional_and_shared(tmp_path: Path) -> None:
    """A configured notice file must create one shared bus."""
    from starlette.applications import Starlette

    app = Starlette()
    config = SiteConfig.from_dict({"invalidation_file": str(tmp_path / "notices.log")})
    engine = attach_from_config(app, config)
    assert engine.invalidation_bus is not None
    assert engine.get_status()["configuration"]["invalidation"] == "shared"
