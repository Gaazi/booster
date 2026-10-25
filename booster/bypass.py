"""Count why a response was not stored, without recording request data.

The counters hold fixed reason names only. No URL, path, token, cookie or
payload is stored, so the snapshot can be shown to an operator or embedded in a
host dashboard.
"""

from collections import Counter
from threading import RLock
from typing import Dict

METHOD = "method_not_read"
POLICY = "route_not_selected"
CREDENTIALS = "credentialed_request"
PERSONALIZED = "personalized_scope"
REQUEST_DIRECTIVE = "request_directive"
RESPONSE_DIRECTIVE = "response_not_public"
STATUS = "status_not_cacheable"
ENCODED = "already_encoded"
STREAMED = "streamed_response"
TOO_LARGE = "body_too_large"
STORED = "stored"


class BypassTracker:
    """Accumulate bounded reason counters for the served responses."""

    def __init__(self) -> None:
        """Start with empty counters."""
        self._lock = RLock()
        self._counts: Counter[str] = Counter()

    def record(self, reason: str) -> None:
        """Count one decision for a served response."""
        with self._lock:
            self._counts[reason] += 1

    def get_counts(self) -> Dict[str, int]:
        """Return the reason counters as a stable sorted mapping."""
        with self._lock:
            return dict(sorted(self._counts.items()))

    def reset(self) -> None:
        """Clear every counter."""
        with self._lock:
            self._counts.clear()
