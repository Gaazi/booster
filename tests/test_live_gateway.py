"""Real-socket verification of the nested-folder plugin and both local origins."""

from __future__ import annotations
from typing import Any, Callable, AsyncIterator, Iterator

import json
from pathlib import Path
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]


class OriginHandler(BaseHTTPRequestHandler):
    """Serve a small public JSON origin for live gateway checks."""

    def do_GET(self) -> None:
        """Return a public JSON representation of the requested path."""
        body = json.dumps({"path": self.path}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "public")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:
        """Keep local integration requests out of noisy terminal output."""


@pytest.fixture
def origin_server() -> Iterator[str]:
    """Run an isolated origin on an OS-assigned port and cleanly release it."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), OriginHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def wait_ready(client: Any, process: Any) -> Any:
    """Bound readiness probing and fail visibly if either local server cannot start."""
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        assert process.poll() is None, "Plugin exited before startup completed"
        try:
            if client.get("http://127.0.0.1:5050/api/stats").status_code == 200:
                if client.get("http://127.0.0.1:5051/ready").status_code == 200:
                    return
        except httpx.RequestError:
            pass
        time.sleep(0.05)
    pytest.fail("Local plugin did not become ready within 10 seconds")


def test_live_plugin_from_another_working_directory(origin_server: str, tmp_path: Path) -> None:
    """The packaged launcher serves assets and isolates management over real sockets."""
    log = (tmp_path / "plugin.log").open("w+")
    process = subprocess.Popen([sys.executable, str(ROOT / "run.py"), "--target", origin_server,
                                "--no-browser"], cwd=tmp_path, stdout=log, stderr=log)
    try:
        with httpx.Client(timeout=1, trust_env=False) as client:
            wait_ready(client, process)
            assert client.get("http://127.0.0.1:5050/").status_code == 200
            assert client.get("http://127.0.0.1:5050/dashboard-static/dashboard.js").status_code == 200
            first = client.get("http://127.0.0.1:5051/items?q=2")
            second = client.get("http://127.0.0.1:5051/items?q=2")
            assert first.json() == second.json() == {"path": "/items?q=2"}
            assert first.headers["etag"] == second.headers["etag"]
            assert client.post("http://127.0.0.1:5050/api/clear-cache", headers={
                "Origin": "http://127.0.0.1:5051", "X-Go-Fast-Admin": "1"}).status_code == 403
            assert client.get("http://127.0.0.1:5051/api/stats").json() == {"path": "/api/stats"}
    finally:
        process.terminate()
        process.wait(timeout=10)
        log.close()
