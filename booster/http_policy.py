"""Conservative shared cache and HTTP header policy."""

import math
import time

HOP_HEADERS = {"host", "connection", "keep-alive", "proxy-authenticate",
               "proxy-authorization", "te", "trailer", "transfer-encoding", "upgrade"}


STATIC_EXTENSIONS = (
    ".css", ".js", ".mjs", ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".map"
)


def is_static_asset(path: str) -> bool:
    """Check if the path represents an immutable or public static asset."""
    clean = path.split("?")[0].lower()
    return clean.startswith(("/static/", "/assets/", "/public/")) or clean.endswith(STATIC_EXTENSIONS)


def cache_directives(headers: dict[str, str]) -> set[str]:
    """Parse case-insensitive cache directive names without substring matches."""
    return {part.strip().split("=", 1)[0].lower()
            for part in headers.get("cache-control", "").split(",")}


def request_cacheable(headers: dict[str, str], is_static: bool = False) -> bool:
    """Exclude personalized, conditional and explicitly uncached requests."""
    blocked = {"range", "if-range", "transfer-encoding",
               "if-match", "if-unmodified-since", "if-modified-since"}
    blocked = blocked | {"authorization", "cookie"}
    control = cache_directives(headers)
    return (not blocked.intersection(headers)
            and headers.get("content-length", "0") == "0"
            and not control.intersection({"no-cache", "no-store", "max-age"})
            and "no-cache" not in headers.get("pragma", "").lower())


def response_age(headers: dict[str, str]) -> float:
    """Read the Age header as the number of seconds the response is already old."""
    value = headers.get("age", "0").strip()
    return float(value) if value.isascii() and value.isdigit() else math.inf


def cached_response_age(headers: list[tuple[bytes, bytes]], created_at: float) -> str:
    """Advance the origin age by monotonic resident time for every adapter."""
    values = [value.decode("latin1") for key, value in headers if key.lower() == b"age"]
    age = response_age({"age": ",".join(values)}) if values else 0
    return str(int(age + max(0, time.monotonic() - created_at)))


def response_cacheable(headers: dict[str, str], is_static: bool = False,
                       allowed_vary: tuple[str, ...] = ()) -> bool:
    """Store only responses safe for a shared representation cache."""
    control = cache_directives(headers)
    vary = {part.strip().lower() for part in headers.get("vary", "").split(",") if part.strip()}
    accepted = {"accept-encoding"} | {field.lower() for field in allowed_vary}
    if is_static:
        if any(key in headers for key in ("set-cookie", "content-range", "www-authenticate",
                                         "content-encoding", "expires")):
            return False
        if control.intersection({"private", "no-store", "no-cache", "no-transform", "must-revalidate"}):
            return False
        return "public" in control and vary <= accepted and response_ttl(headers, 300) > 0

    return ("public" in control and not any(key in headers for key in
            ("set-cookie", "content-encoding", "content-range", "www-authenticate"))
            and not control.intersection({"private", "no-store", "no-cache", "no-transform",
                                          "max-age", "s-maxage", "must-revalidate"})
            and "expires" not in headers and "age" not in headers
            and vary <= accepted)


def response_ttl(headers: dict[str, str], default: float) -> float:
    """Bound static cache retention by the shortest declared freshness limit."""
    limits = [default]
    age = response_age(headers)
    if not math.isfinite(age):
        return 0
    for part in headers.get("cache-control", "").split(","):
        name, separator, value = part.strip().partition("=")
        if name.lower() in {"max-age", "s-maxage"}:
            if not separator or not value.strip('"').isdigit():
                return 0
            limits.append(float(value.strip('"')) - age)
    return max(0, min(limits))


def filtered_headers(headers: list[tuple[bytes, bytes]]) -> list[tuple[bytes, bytes]]:
    """Remove hop-by-hop fields including fields nominated by Connection."""
    connection = {part.strip().lower() for k, v in headers if k.lower() == b"connection"
                  for part in v.decode("latin1").split(",")}
    blocked = HOP_HEADERS | connection
    return [(k.lower(), v) for k, v in headers if k.decode("latin1").lower() not in blocked]


def merge_vary(value: str) -> str:
    """Preserve existing negotiation fields while adding compression."""
    fields = [part.strip() for part in value.split(",") if part.strip()]
    if "*" not in fields and "accept-encoding" not in {part.lower() for part in fields}:
        fields.append("Accept-Encoding")
    return ", ".join(fields)
