"""Bounded, fail-closed sampling of *real* server-sent events.

Playwright route.fetch buffers the complete body and cannot consume an endless
SSE response. This adapter reads only through the first complete real data
message from the authorized server; it is NOT an infinite streaming proxy.
Redirects are never followed. No cookies or site authentication are forwarded.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

import httpx


@dataclass(frozen=True, slots=True)
class SseSample:
    status: int
    body: bytes


def _first_complete_message(buffer: bytes) -> bytes | None:
    """Return prefix through the first complete `data:` event, not comments."""
    # Keep offsets in the *original* bytes rather than returning normalized text.
    # Both CRLF and LF are supported as complete SSE frame separators.
    offset = 0
    while offset < len(buffer):
        lf = buffer.find(b"\n\n", offset)
        crlf = buffer.find(b"\r\n\r\n", offset)
        choices = [(pos, size) for pos, size in ((lf, 2), (crlf, 4)) if pos >= 0]
        if not choices:
            return None
        pos, size = min(choices)
        frame = buffer[offset:pos].replace(b"\r\n", b"\n")
        if any(line.startswith(b"data:") for line in frame.split(b"\n")):
            return bytes(buffer[:pos + size])
        offset = pos + size
    return None


async def sample_sse(
    url: str, *, transport: httpx.AsyncBaseTransport | None = None,
    max_bytes: int = 32768, timeout_seconds: float = 5.0,
) -> SseSample | None:
    """Read one authentic SSE data frame; reject redirects and unbounded data.

    Caller must have already enforced URL scope and acquired RequestGate.
    No follow-up requests are made by this function, even for same-host 302.
    """
    try:
        async with asyncio.timeout(timeout_seconds):
            async with httpx.AsyncClient(
                transport=transport, follow_redirects=False,
                trust_env=transport is None,
                timeout=httpx.Timeout(3.0, connect=3.0),
                headers={"Accept": "text/event-stream", "User-Agent": "API-Extractor/0.1.0"},
            ) as client:
                async with client.stream("GET", url) as response:
                    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                    if response.status_code != 200 or content_type != "text/event-stream":
                        return None
                    buffer = bytearray()
                    async for chunk in response.aiter_bytes():
                        if len(buffer) + len(chunk) > max_bytes:
                            return None
                        buffer.extend(chunk)
                        message = _first_complete_message(buffer)
                        if message is not None:
                            return SseSample(status=200, body=message)
                    return None
    except (TimeoutError, httpx.HTTPError, ValueError):
        return None
