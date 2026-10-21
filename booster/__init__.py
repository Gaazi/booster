"""booster - Ultra-fast, zero-config caching, minification, and compression engine."""

from importlib import import_module
from typing import Any, TYPE_CHECKING

from booster.booster import RocketBooster
from booster.cache import FastMemoryCache
from booster.compressor import ResponseCompressor
from booster.minifier import FastMinifier
from booster.telemetry import TelemetryTracker
from booster.cache_policy import CachePolicy
from booster.invalidation import FileInvalidationBus, LocalInvalidationBus
from booster.site_config import SiteConfig, attach_from_config

if TYPE_CHECKING:
    from booster.cdn import CDNConfig, CDNManager
    from booster.django_support import DjangoRocketMiddleware
    from booster.proxy import SpeedProxyServer

_OPTIONAL_EXPORTS = {
    "CDNConfig": ("booster.cdn", "cdn"),
    "CDNManager": ("booster.cdn", "cdn"),
    "DjangoRocketMiddleware": ("booster.django_support", ""),
    "SpeedProxyServer": ("booster.proxy", "server"),
}

__version__ = "1.0.2.dev1"

# Direct top-level helper for maximum simplicity
attach = RocketBooster.attach


def __getattr__(name: str) -> Any:
    """Load optional integrations only when requested, preserving public exports."""
    if name not in _OPTIONAL_EXPORTS:
        raise AttributeError(f"module 'booster' has no attribute {name!r}")
    module, extra = _OPTIONAL_EXPORTS[name]
    try:
        value = getattr(import_module(module), name)
    except ModuleNotFoundError as error:
        if extra and error.name in {"httpx", "starlette", "fastapi", "uvicorn"}:
            raise ImportError(f"{name} requires the optional booster[{extra}] installation") from error
        raise
    globals()[name] = value
    return value

__all__ = [
    "RocketBooster",
    "FastMemoryCache",
    "ResponseCompressor",
    "FastMinifier",
    "SpeedProxyServer",
    "DjangoRocketMiddleware",
    "TelemetryTracker",
    "CDNManager",
    "CDNConfig",
    "attach",
    "CachePolicy",
    "FileInvalidationBus",
    "LocalInvalidationBus",
    "SiteConfig",
    "attach_from_config",
]
