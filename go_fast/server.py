"""One-Click Dashboard and Standalone Accelerator Gateway server."""

import asyncio
import argparse
import signal
import socket
import webbrowser
from contextlib import asynccontextmanager
from threading import Timer
from pathlib import Path
from typing import AsyncIterator, Dict
from types import FrameType

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles

from go_fast.proxy import SpeedProxyServer
from go_fast.local_security import LocalAccessGuard

@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Close pooled upstream connections when the gateway stops."""
    yield
    await proxy.close()


app = FastAPI(title="go_fast Accelerator", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.add_middleware(LocalAccessGuard)
gateway = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
gateway.add_middleware(LocalAccessGuard, management=False)
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
    try:
        proxy.set_target(url)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
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
    return JSONResponse({"found_url": await find_local_target()})


async def find_local_target() -> str | None:
    """Find a development server with concurrent bounded loopback probes."""
    common_ports = [8000, 3000, 8080, 5000, 4200, 8001]
    found_url = None
    results = await asyncio.gather(*(asyncio.to_thread(is_port_open, port) for port in common_ports))
    for port, available in zip(common_ports, results):
        if available:
            found_url = f"http://127.0.0.1:{port}"
            break
    return found_url


@app.api_route("/site/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def gateway_redirect(request: Request, path: str) -> RedirectResponse:
    """Keep old gateway links working on the isolated upstream origin."""
    raw_path = request.scope.get("raw_path", b"/site/").decode("ascii")
    query = request.scope.get("query_string", b"").decode("ascii")
    return RedirectResponse("http://127.0.0.1:5051" + raw_path + ("?" + query if query else ""), status_code=307)


@gateway.api_route("/site/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
@gateway.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def proxy_gateway(request: Request, path: str) -> Response:
    """Proxy requests through the caching and optimization engine."""
    return await proxy.handle_request(request)


def launch_browser() -> None:
    """Open user browser to the dashboard."""
    webbrowser.open("http://127.0.0.1:5050")


def main() -> None:
    """Launch the local dashboard and acceleration gateway."""
    parser = argparse.ArgumentParser(description="Start the local go_fast plugin")
    parser.add_argument("--target", help="Trusted HTTP/HTTPS upstream base URL")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser")
    arguments = parser.parse_args()
    if arguments.target:
        proxy.set_target(arguments.target)
    print("Dashboard: http://127.0.0.1:5050")
    print("Accelerated Gateway: http://127.0.0.1:5051/")
    asyncio.run(serve_local(arguments.target, not arguments.no_browser))


async def serve_local(target: str | None = None, open_browser: bool = True) -> None:
    """Run dashboard and gateway on separate origins with shared lifecycle."""
    if not target:
        detected = await find_local_target()
        if detected:
            proxy.set_target(detected)
    if any(is_port_open(port) for port in (5050, 5051)):
        raise OSError("Ports 5050 and 5051 must be available for the local plugin")
    servers = [uvicorn.Server(uvicorn.Config(application, host="127.0.0.1", port=port,
                                           log_level="warning", proxy_headers=False,
                                           limit_concurrency=64, timeout_keep_alive=5))
               for application, port in ((app, 5050), (gateway, 5051))]
    def stop_servers(signum: int, frame: FrameType | None) -> None:
        """Stop both origins together on a terminal interrupt or termination."""
        for server in servers:
            server.should_exit = True
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, stop_servers)
    if open_browser:
        Timer(1.0, launch_browser).start()
    try:
        await asyncio.gather(*(server._serve() for server in servers))
    finally:
        await proxy.close()


if __name__ == "__main__":
    main()
