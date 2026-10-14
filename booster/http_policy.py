"""Conservative shared cache and HTTP header policy."""

HOP_HEADERS = {"host", "connection", "keep-alive", "proxy-authenticate",
               "proxy-authorization", "te", "trailer", "transfer-encoding", "upgrade"}


def cache_directives(headers: dict[str, str]) -> set[str]:
    """Parse case-insensitive cache directive names without substring matches."""
    return {part.strip().split("=", 1)[0].lower()
            for part in headers.get("cache-control", "").split(",")}


def request_cacheable(headers: dict[str, str]) -> bool:
    """Exclude personalized, conditional and explicitly uncached requests."""
    blocked = {"authorization", "cookie", "range", "if-range", "transfer-encoding",
               "if-match", "if-unmodified-since", "if-modified-since"}
    control = cache_directives(headers)
    return (not blocked.intersection(headers)
            and headers.get("content-length", "0") == "0"
            and not control.intersection({"no-cache", "no-store", "max-age"})
            and "no-cache" not in headers.get("pragma", "").lower())


def response_cacheable(headers: dict[str, str]) -> bool:
    """Store only responses safe for a shared representation cache."""
    control = cache_directives(headers)
    vary = {part.strip().lower() for part in headers.get("vary", "").split(",") if part.strip()}
    return ("public" in control and not any(key in headers for key in
            ("set-cookie", "content-encoding", "content-range", "www-authenticate"))
            and not control.intersection({"private", "no-store", "no-cache", "no-transform",
                                          "max-age", "s-maxage", "must-revalidate"})
            and "expires" not in headers and "age" not in headers
            and vary <= {"accept-encoding"})


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
