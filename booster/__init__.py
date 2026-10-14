"""booster - Ultra-fast, zero-config caching, minification, and compression engine."""

from booster.booster import RocketBooster
from booster.cache import FastMemoryCache
from booster.compressor import ResponseCompressor
from booster.cdn import CDNConfig, CDNManager
from booster.django_support import DjangoRocketMiddleware
from booster.minifier import FastMinifier
from booster.proxy import SpeedProxyServer
from booster.telemetry import TelemetryTracker

__version__ = "1.0.0"

# Direct top-level helper for maximum simplicity
attach = RocketBooster.attach

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
]
