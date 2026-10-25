"""Enforce loopback access and isolate the dashboard from upstream pages."""

import ipaddress
from urllib.parse import urlsplit
from typing import Any, Callable

from starlette.responses import JSONResponse

from booster.asgi_response import parse_headers

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def validate_target(url: str) -> str:
    """Reject credentials, malformed ports, special networks and gateway loops."""
    parsed = urlsplit(url)
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or any(ord(c) <= 32 for c in url)
            or "\\" in url):
        raise ValueError("Enter an HTTP or HTTPS base URL without credentials")
    host = parsed.hostname.lower()
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None:
        address = getattr(address, "ipv4_mapped", None) or address
        if address.is_link_local or address.is_unspecified or address.is_multicast:
            raise ValueError("Special network addresses are not permitted")
    local = host in LOCAL_HOSTS or (address is not None and address.is_loopback)
    if local and port in {5050, 5051}:
        raise ValueError("The gateway cannot proxy itself")
    return url.rstrip("/")


class LocalAccessGuard:
    """Block remote clients, DNS rebinding and browser requests from other origins."""

    def __init__(self, app: Any, management: bool = True) -> None:
        """Select management restrictions or the isolated gateway access policy."""
        self.app, self.management = app, management

    async def __call__(self, scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        """Validate raw host and peer before routing any HTTP request."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = parse_headers(scope.get("headers", []))
        error = self._error(scope, headers)
        if error:
            await JSONResponse({"error": error}, status_code=403)(scope, receive, send)
            return
        async def secure_send(message: dict[str, Any]) -> None:
            """Make management responses private and prevent framing or sniffing."""
            if self.management and message["type"] == "http.response.start":
                original = message.get("headers", [])
                protected = {b"cache-control", b"x-frame-options", b"referrer-policy"}
                message = {**message, "headers": [(k, v) for k, v in original if k.lower() not in protected]
                           + [(b"cache-control", b"no-store"), (b"x-frame-options", b"DENY"),
                              (b"referrer-policy", b"no-referrer"), (b"x-content-type-options", b"nosniff")]}
            await send(message)
        await self.app(scope, receive, secure_send)

    def _error(self, scope: dict[str, Any], headers: dict[str, str]) -> str | None:
        """Return the precise failed local browser access boundary."""
        authority = headers.get("host", "")
        try:
            host = urlsplit("http://" + authority).hostname
            peer = scope.get("client", ("", 0))[0]
            local_peer = ipaddress.ip_address(peer).is_loopback
        except ValueError:
            return "Invalid local address"
        if host not in LOCAL_HOSTS or not local_peer or "," in authority or "@" in authority:
            return "Only loopback clients and hosts are permitted"
        if (not self.management and scope.get("method") in {"GET", "HEAD"}
                and headers.get("sec-fetch-mode") == "navigate"
                and headers.get("sec-fetch-dest") == "document"):
            return None
        origin = headers.get("origin")
        expected = scope.get("scheme", "http") + "://" + authority
        if origin is not None and origin != expected:
            return "Foreign origins cannot access the local plugin"
        if headers.get("sec-fetch-site", "none") not in {"same-origin", "none"}:
            return "Foreign browser requests cannot access the local plugin"
        if self.management and scope.get("method") not in {"GET", "HEAD", "OPTIONS"}:
            if headers.get("x-booster-admin") != "1":
                return "Management writes require the dashboard request header"
        return None
