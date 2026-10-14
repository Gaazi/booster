"""Unit tests for ResponseCompressor."""

import gzip
from booster.compressor import ResponseCompressor, choose_encoding, is_compressible


def test_is_compressible() -> None:
    assert is_compressible("text/html; charset=utf-8", min_size=100, content_length=500)
    assert is_compressible("application/json", min_size=100, content_length=500)
    assert not is_compressible("image/png", min_size=100, content_length=500)
    assert not is_compressible("text/html", min_size=500, content_length=100)


def test_choose_encoding() -> None:
    assert choose_encoding("gzip, deflate, br") == "br"
    assert choose_encoding("gzip, deflate") == "gzip"
    assert choose_encoding("identity") is None


def test_compress_payload() -> None:
    compressor = ResponseCompressor(min_size=50)
    payload = b"A" * 1000

    compressed, encoding = compressor.compress(payload, "text/plain", "gzip")
    assert encoding == "gzip"
    assert len(compressed) < len(payload)
    decompressed = gzip.decompress(compressed)
    assert decompressed == payload
