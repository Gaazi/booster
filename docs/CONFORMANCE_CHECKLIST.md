# Conformance Checklist

Copy the file below into the host project's test suite, fill the four marked
slots and run it. Every check is a privacy or correctness boundary Booster
promises. The template was executed against a real Starlette application with
Booster attached; all five checks passed, and the security-header check failed
when the outer middleware was missing — so the checks detect real regressions.

Run with:

```bash
python -m pytest -q tests/test_booster_conformance.py
```

```python
"""Booster conformance checks for a host application."""

from __future__ import annotations

import asyncio
from typing import Any

# --- FILL THESE FOUR SLOTS -----------------------------------------------
from myapp.booster_plugin import engine   # the RocketBooster instance you attached
from myapp.main import app                 # the ASGI application you protect

PUBLIC_PATH = "/static/app.css"      # a route your app serves as public
PRIVATE_PATH = "/account"            # a route that is per visitor
MUTATION_PATH = "/catalog"           # a route that writes, then reads
SECURITY_HEADER = b"x-frame-options"  # a header your own middleware always sets
# -------------------------------------------------------------------------


def build_scope(method: str, path: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    """Build a minimal HTTP scope without any HTTP client dependency."""
    raw = [(b"host", b"conformance.test")]
    for name, value in (headers or {}).items():
        raw.append((name.lower().encode("ascii"), value.encode("ascii")))
    return {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": method, "scheme": "http", "path": path,
            "raw_path": path.encode("utf-8"), "query_string": b"",
            "headers": raw, "client": ("127.0.0.1", 50000), "server": ("conformance.test", 80)}


async def call(app: Any, method: str, path: str, headers: dict[str, str] | None = None):
    """Drive one ASGI request and collect status, body and headers."""
    body = bytearray()
    status = 0
    response_headers: list[tuple[bytes, bytes]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        nonlocal status
        if message["type"] == "http.response.start":
            status = message["status"]
            response_headers.extend(message.get("headers", []))
        elif message["type"] == "http.response.body":
            body.extend(message.get("body", b""))

    await app(build_scope(method, path, headers), receive, send)
    return status, bytes(body), response_headers


def request(method: str, path: str, headers: dict[str, str] | None = None):
    """Send one request to the host application."""
    return asyncio.run(call(app, method, path, headers))


def hits() -> int:
    """Read the engine cache-hit counter."""
    return engine.get_status()["metrics"]["cache_hits"]


def test_public_route_is_served_from_cache() -> None:
    """A repeated public request must be answered from the cache."""
    first = request("GET", PUBLIC_PATH)
    before = hits()
    second = request("GET", PUBLIC_PATH)
    assert first[0] == second[0] == 200
    assert first[1] == second[1]
    assert hits() == before + 1, "second request was not served from the cache"


def test_credentialed_request_never_uses_the_cache() -> None:
    """A cookie-bearing request must always reach the application."""
    request("GET", PUBLIC_PATH)
    before = hits()
    status, _, _ = request("GET", PUBLIC_PATH, {"cookie": "session=abc"})
    assert status == 200
    assert hits() == before, "a credentialed request was served from the cache"


def test_private_route_is_not_stored() -> None:
    """A personalized response must never come from the shared cache."""
    before = hits()
    request("GET", PRIVATE_PATH, {"cookie": "session=abc"})
    request("GET", PRIVATE_PATH, {"cookie": "session=abc"})
    assert hits() == before, "a personalized response was served from the cache"


def test_mutation_invalidates_the_cache() -> None:
    """A write must invalidate the cached read of the same route."""
    request("GET", PUBLIC_PATH)
    request("POST", MUTATION_PATH)
    before = hits()
    request("GET", PUBLIC_PATH)
    assert hits() == before, "the cached entry survived a write"


def test_security_headers_survive_a_cache_hit() -> None:
    """Outer security middleware must still decorate a cached response."""
    request("GET", PUBLIC_PATH)
    status, _, headers = request("GET", PUBLIC_PATH)
    assert status == 200
    assert any(name.lower() == SECURITY_HEADER for name, _ in headers), \
        "security headers are missing on a cache hit"
```

## Manual checks the test file cannot cover

| Check | Expected |
| :--- | :--- |
| Response bytes identical with and without Booster | same decoded bytes |
| Range requests (`Range: bytes=…`) | bypass the cache |
| Signed upload and download URLs | never stored |
| `Cache-Control: private` origin response | never stored |
| Worker count × `max_cache_bytes` | fits the host memory budget |
| Deploy with changed assets | versioned asset URLs avoid a purge |

If a check fails, fix the route policy in the adapter file rather than
relaxing the test.
