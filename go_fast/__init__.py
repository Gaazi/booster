"""go_fast - Ultra-fast, zero-config caching, minification, and compression engine."""

from go_fast.booster import RocketBooster
from go_fast.cache import FastMemoryCache
from go_fast.compressor import ResponseCompressor
from go_fast.django_support import DjangoRocketMiddleware
from go_fast.minifier import FastMinifier
from go_fast.proxy import SpeedProxyServer
from go_fast.telemetry import TelemetryTracker

__version__ = "1.0.0"

__all__ = [
    "RocketBooster",
    "FastMemoryCache",
    "ResponseCompressor",
    "FastMinifier",
    "SpeedProxyServer",
    "DjangoRocketMiddleware",
    "TelemetryTracker",
]
