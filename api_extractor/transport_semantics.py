"""Classify observed Socket.IO transport requests without exposing session IDs.

Engine.IO/Socket.IO polling and WebSocket handshakes are protocol transport,
not ordinary business REST operations. Preserve original wire method and HAR.
"""
from __future__ import annotations

from urllib.parse import parse_qsl, urlsplit


def socketio_transport_note(url: str, method: str, resource_type: object) -> str | None:
    """Give bounded protocol labels only when the actual transport is explicit."""
    if not isinstance(url, str) or not isinstance(resource_type, str):
        return None
    try:
        parsed = urlsplit(url)
        last_segment = parsed.path.rstrip("/").rsplit("/", 1)[-1].lower()
        if last_segment not in {"socket.io", "engine.io"}:
            return None
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    except (TypeError, ValueError, UnicodeError):
        return None
    # Engine.IO uses EIO=<version> and transport=polling|websocket. These
    # values are read solely to classify; sid and data values are never emitted.
    version = query.get("EIO", "")
    transport = query.get("transport", "")
    if not (version.isdecimal() and 0 < len(version) <= 2):
        return None
    wire_method = method.upper()
    if transport == "polling" and wire_method in {"GET", "POST"} and resource_type in {"xhr", "fetch"}:
        return "Socket.IO HTTP polling transport observed (not business REST)"
    if transport == "websocket" and wire_method == "WS" and resource_type == "websocket":
        return "Socket.IO WebSocket transport handshake observed (not business REST)"
    return None
