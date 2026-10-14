"""High-performance Brotli and Gzip HTTP response compression engine."""

import gzip
from functools import lru_cache
import zlib
from typing import Optional, Set, Tuple

try:
    import brotli
    HAS_BROTLI = True
except ImportError:
    HAS_BROTLI = False

COMPRESSIBLE_TYPES: Set[str] = {
    "text/html",
    "text/css",
    "text/plain",
    "text/xml",
    "text/javascript",
    "application/javascript",
    "application/x-javascript",
    "application/json",
    "application/xml",
    "application/ld+json",
    "application/manifest+json",
    "image/svg+xml",
}


def is_compressible(content_type: str, min_size: int, content_length: int) -> bool:
    """Determine if content type and payload size qualify for compression."""
    if content_length < min_size:
        return False
    base_type = content_type.split(";")[0].strip().lower()
    return base_type in COMPRESSIBLE_TYPES


def choose_encoding(accept_encoding: str) -> Optional[str]:
    """Select the best compression algorithm supported by client."""
    qualities = {}
    for item in accept_encoding.lower().split(","):
        parts = item.strip().split(";")
        quality = 1.0
        for parameter in parts[1:]:
            name, _, value = parameter.strip().partition("=")
            if name == "q":
                try:
                    quality = float(value)
                except ValueError:
                    quality = 0.0
        qualities[parts[0]] = quality if 0 <= quality <= 1 else 0.0
    supported = (["br"] if HAS_BROTLI else []) + ["gzip", "deflate"]
    ranked = sorted(supported, key=lambda x: qualities.get(x, qualities.get("*", 0)), reverse=True)
    return next((x for x in ranked if qualities.get(x, qualities.get("*", 0)) > 0), None)



@lru_cache(maxsize=64)
def compress_payload(content: bytes, encoding: str) -> bytes:
    """Compress bytes using chosen encoding."""
    if encoding == "br" and HAS_BROTLI:
        return brotli.compress(content, quality=4)
    if encoding == "gzip":
        return gzip.compress(content, compresslevel=6)
    if encoding == "deflate":
        return zlib.compress(content, level=6)
    return content


class ResponseCompressor:
    """Handles adaptive payload compression according to client headers."""

    def __init__(self, min_size: int = 512) -> None:
        """Set the minimum payload size eligible for public-response compression."""
        self.min_size = min_size

    def compress(
        self,
        content: bytes,
        content_type: str,
        accept_encoding: str,
    ) -> Tuple[bytes, Optional[str]]:
        """Compress content if eligible, returning compressed bytes and encoding."""
        if not is_compressible(content_type, self.min_size, len(content)):
            return content, None

        encoding = choose_encoding(accept_encoding)
        if not encoding:
            return content, None

        compressed = (compress_payload(content, encoding) if len(content) <= 65536
                      else compress_payload.__wrapped__(content, encoding))
        if len(compressed) >= len(content):
            return content, None

        return compressed, encoding
