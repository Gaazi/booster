"""Compatibility entrypoint for the packaged go_fast local gateway."""

from go_fast.server import (
    app, gateway, proxy, main, lifespan, serve_dashboard, get_stats, set_target,
    clear_cache, is_port_open, detect_local, gateway_redirect, proxy_gateway,
    launch_browser, serve_local,
)

if __name__ == "__main__":
    main()
