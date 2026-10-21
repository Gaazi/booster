"""Verify the measurement helper against a local fixture server."""

import http.server
import threading
from typing import Any

import pytest

from booster.measurement import cache_verdict, fetch_once, format_report, measure, measure_or_error


class Fixture(http.server.BaseHTTPRequestHandler):
    """Serve one public asset and one private page."""

    calls = 0

    def do_GET(self) -> None:
        """Answer with the policy of the requested path."""
        Fixture.calls += 1
        if self.path.startswith("/private"):
            body, control = b"secret", "private, no-store"
        else:
            body, control = b"body{color:red}", "public, max-age=120"
        self.send_response(200)
        self.send_header("Content-Type", "text/css" if body.startswith(b"body") else "text/plain")
        self.send_header("Cache-Control", control)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        """Keep the test output clean."""


@pytest.fixture()
def server_url() -> str:
    """Run the fixture server and return its base URL."""
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Fixture)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def test_fetch_once_reports_the_response(server_url: str) -> None:
    """One fetch must report the status, size and headers."""
    result = fetch_once(f"{server_url}/static/app.css")
    assert result["status"] == 200
    assert result["bytes"] == len(b"body{color:red}")
    assert result["headers"]["Cache-Control"] == "public, max-age=120"


def test_measure_reports_percentiles_and_the_verdict(server_url: str) -> None:
    """The report must carry the percentiles and the engine's own verdict."""
    report = measure(f"{server_url}/static/app.css", requests=5)
    assert report["samples"] == 5
    assert report["status"] == 200
    assert report["verdict"]["cacheable"] is True
    assert report["verdict"]["ttl_seconds"] == 120
    assert report["p50_ms"] >= 0 and report["p95_ms"] >= 0
    assert "booster" in format_report(report)


def test_private_response_is_reported_as_not_cacheable(server_url: str) -> None:
    """A private response must never be reported as cacheable."""
    report = measure(f"{server_url}/private/account", requests=2)
    assert report["verdict"]["cacheable"] is False
    assert report["verdict"]["reason"] == "response_not_public"


def test_unreachable_url_returns_no_report() -> None:
    """An unreachable URL must be reported as unreachable, not as a crash."""
    assert measure_or_error("http://127.0.0.1:1/nothing", requests=1, timeout=2) is None


def test_verdict_explains_a_non_public_status() -> None:
    """A non-200 response must not be reported as cacheable."""
    verdict = cache_verdict("http://example.test/page", {"cache-control": "public"}, 404)
    assert verdict["cacheable"] is False
    assert verdict["reason"] == "status_not_cacheable"
