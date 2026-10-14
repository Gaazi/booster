"""One-Click Dashboard and Standalone Accelerator Gateway server."""

import asyncio
import os
import socket
import webbrowser
from contextlib import asynccontextmanager
from threading import Timer
from urllib.parse import urlsplit
from pathlib import Path
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from go_fast.proxy import SpeedProxyServer

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Close pooled upstream connections when the gateway stops."""
    yield
    await proxy.close()


app = FastAPI(title="go_fast Accelerator", docs_url=None, redoc_url=None, lifespan=lifespan)
proxy = SpeedProxyServer(target_url="http://127.0.0.1:8000")

BASE_DIR = Path(__file__).resolve().parent
DASHBOARD_DIR = BASE_DIR / "dashboard"

if DASHBOARD_DIR.exists():
    app.mount("/dashboard-static", StaticFiles(directory=str(DASHBOARD_DIR)), name="dashboard-static")


@app.get("/")
async def serve_dashboard() -> FileResponse:
    """Serve the management and telemetry dashboard."""
    index_path = DASHBOARD_DIR / "index.html"
    return FileResponse(str(index_path))


@app.get("/api/stats")
async def get_stats() -> JSONResponse:
    """Return live telemetry metrics and cache status."""
    stats = proxy.telemetry.get_stats()
    stats["target_url"] = proxy.target_url
    stats["cache_count"] = proxy.cache.count()
    return JSONResponse(stats)


@app.post("/api/set-target")
async def set_target(payload: Dict[str, str]) -> JSONResponse:
    """Update target website URL for the accelerator."""
    url = payload.get("url", "").strip()
    if not url:
        return JSONResponse({"error": "URL cannot be empty"}, status_code=400)
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.query or parsed.fragment:
        return JSONResponse({"error": "Enter an HTTP or HTTPS base URL"}, status_code=400)
    proxy.set_target(url)
    return JSONResponse({"status": "ok", "target_url": proxy.target_url})


@app.post("/api/clear-cache")
async def clear_cache() -> JSONResponse:
    """Flush in-memory cache and reset telemetry."""
    proxy.cache.clear()
    proxy.telemetry.reset()
    return JSONResponse({"status": "cleared"})


def is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    """Quickly check if a local port has an active listening server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) == 0


@app.get("/api/detect-local")
async def detect_local() -> JSONResponse:
    """Scan common development ports for running applications."""
    common_ports = [8000, 3000, 8080, 5000, 4200, 8001]
    found_url = None
    results = await asyncio.gather(*(asyncio.to_thread(is_port_open, port) for port in common_ports))
    for port, available in zip(common_ports, results):
        if available:
            found_url = f"http://127.0.0.1:{port}"
            break
    return JSONResponse({"found_url": found_url})


@app.api_route("/site/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def proxy_gateway(request: Request, path: str) -> Response:
    """Proxy requests through the caching and optimization engine."""
    return await proxy.handle_request(request)


def launch_browser() -> None:
    """Open user browser to the dashboard."""
    webbrowser.open("http://127.0.0.1:5050")


def main() -> None:
    """Launch the local dashboard and acceleration gateway."""
    Timer(1.0, launch_browser).start()
    print("\n" + "=" * 60)
    print("🚀 go_fast Rocket Speed Accelerator is launching!")
    print("👉 Dashboard: http://127.0.0.1:5050")
    print("👉 Accelerated Gateway: http://127.0.0.1:5050/site/")
    print("=" * 60 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=5050, log_level="warning")


if __name__ == "__main__":
    main()
