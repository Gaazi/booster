"""Conservative shared cache and HTTP header policy."""

HOP_HEADERS = {"host", "connection", "keep-alive", "proxy-authenticate",
               "proxy-authorization", "te", "trailer", "transfer-encoding", "upgrade"}


def request_cacheable(headers: dict[str, str]) -> bool:
    """Exclude personalized, conditional and explicitly uncached requests."""
    blocked = {"authorization", "cookie", "range", "if-range"}
    control = headers.get("cache-control", "").lower()
    return not blocked.intersection(headers) and not any(
        token in control for token in ("no-cache", "no-store", "max-age=0"))


def response_cacheable(headers: dict[str, str]) -> bool:
    """Store only responses safe for a shared representation cache."""
    control = headers.get("cache-control", "").lower()
    vary = {part.strip().lower() for part in headers.get("vary", "").split(",") if part.strip()}
    return not any(key in headers for key in ("set-cookie", "content-encoding")) and not any(
        token in control for token in ("private", "no-store", "no-cache", "no-transform", "max-age")) and vary <= {"accept-encoding"}


def merge_vary(value: str) -> str:
    """Preserve existing negotiation fields while adding compression."""
    fields = [part.strip() for part in value.split(",") if part.strip()]
    if "*" not in fields and "accept-encoding" not in {part.lower() for part in fields}:
        fields.append("Accept-Encoding")
    return ", ".join(fields)
