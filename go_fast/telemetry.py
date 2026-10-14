"""Telemetry and performance metrics tracking for go_fast."""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List
from threading import RLock
from go_fast.cache import synchronized


@dataclass
class RequestLog:
    """Record of an individual processed HTTP request."""
    method: str
    path: str
    status_code: int
    duration_ms: float
    cached: bool
    size_bytes: int
    compression: str
    timestamp: float = field(default_factory=time.time)


class TelemetryTracker:
    """Thread-safe statistics accumulator for the booster engine."""

    def __init__(self, max_logs: int = 50) -> None:
        """Initialize locked counters and a bounded redacted log collection."""
        self.max_logs = max_logs
        self._lock = RLock()
        self.total_requests: int = 0
        self.cache_hits: int = 0
        self.cache_misses: int = 0
        self.raw_bytes: int = 0
        self.served_bytes: int = 0
        self.total_latency_saved_ms: float = 0.0
        self.recent_logs: List[Dict[str, Any]] = []

    @synchronized
    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        cached: bool,
        raw_size: int,
        served_size: int,
        compression: str = "none",
        latency_saved_ms: float = 0.0,
    ) -> None:
        """Record an incoming request and update aggregate statistics."""
        self.total_requests += 1
        if cached:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

        self.raw_bytes += raw_size
        self.served_bytes += served_size
        self.total_latency_saved_ms += max(0.0, latency_saved_ms)

        self._append_log(method, status_code, duration_ms, cached, served_size, compression)

    def _append_log(self, method: str, status_code: int, duration_ms: float, cached: bool,
                    served_size: int, compression: str) -> None:
        """Append one redacted log while the caller holds the telemetry lock."""
        log_entry = {
            "method": method,
            "path": "[redacted]",
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "cached": cached,
            "size_bytes": served_size,
            "compression": compression,
            "time": time.strftime("%H:%M:%S"),
        }
        self.recent_logs.insert(0, log_entry)
        if len(self.recent_logs) > self.max_logs:
            self.recent_logs.pop()

    @synchronized
    def get_stats(self) -> Dict[str, Any]:
        """Return summary metrics for dashboard and monitoring."""
        hit_ratio = (
            (self.cache_hits / self.total_requests * 100)
            if self.total_requests > 0
            else 0.0
        )
        bandwidth_saved = max(0, self.raw_bytes - self.served_bytes)
        savings_percent = (
            (bandwidth_saved / self.raw_bytes * 100)
            if self.raw_bytes > 0
            else 0.0
        )

        return {
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_ratio_percent": round(hit_ratio, 1),
            "bandwidth_saved_bytes": bandwidth_saved,
            "bandwidth_saved_percent": round(savings_percent, 1),
            "total_latency_saved_ms": round(self.total_latency_saved_ms, 1),
            "recent_logs": [dict(log) for log in self.recent_logs[:15]],
        }

    @synchronized
    def reset(self) -> None:
        """Reset all tracked performance metrics."""
        self.total_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.raw_bytes = 0
        self.served_bytes = 0
        self.total_latency_saved_ms = 0.0
        self.recent_logs.clear()
