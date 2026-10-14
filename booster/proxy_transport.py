"""Bounded HTTP proxy transport preserving raw origin representations."""

from typing import AsyncIterator

import httpx
from starlette.requests import Request
from starlette.responses import StreamingResponse

from booster.http_policy import filtered_headers

MAX_BODY = 2_000_000
MAX_REQUEST = 8_000_000


class BodyTooLarge(ValueError):
    """Signal a request exceeding the gateway upload limit."""


async def request_body(request: Request) -> bytes:
    """Bound request buffering even when Content-Length is missing or forged."""
    chunks = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_REQUEST:
            raise BodyTooLarge("Request exceeds the 8 MB limit")
        chunks.append(chunk)
    return b"".join(chunks)


def outgoing_headers(request: Request) -> list[tuple[bytes, bytes]]:
    """Prevent proxy identity spoofing and request unencoded upstream content."""
    blocked = {b"accept-encoding", b"forwarded", b"x-real-ip", b"content-length"}
    headers = [(k, v) for k, v in filtered_headers(request.scope.get("headers", []))
               if k not in blocked and not k.startswith(b"x-forwarded-")]
    return headers + [(b"accept-encoding", b"identity")]


async def upstream_body(response: httpx.Response) -> bytes | StreamingResponse:
    """Buffer small raw responses and stream larger bodies with bounded memory."""
    if response.is_stream_consumed:
        return response.content
    iterator = response.aiter_raw(chunk_size=65536)
    chunks: list[bytes] = []
    size = 0
    try:
        async for chunk in iterator:
            chunks.append(chunk)
            size += len(chunk)
            if size > MAX_BODY:
                result = StreamingResponse(stream_body(response, iterator, chunks),
                                           status_code=response.status_code)
                result.raw_headers = filtered_headers(list(response.headers.raw))
                return result
    except BaseException:
        await response.aclose()
        raise
    await response.aclose()
    return b"".join(chunks)


async def stream_body(response: httpx.Response, iterator: AsyncIterator[bytes],
                      chunks: list[bytes]) -> AsyncIterator[bytes]:
    """Release the pooled connection on completion, cancellation or read failure."""
    try:
        for chunk in chunks:
            yield chunk
        async for chunk in iterator:
            yield chunk
    finally:
        await response.aclose()
