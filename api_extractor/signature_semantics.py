"""Observed S4 signing-field metadata, never signing secrets or replay."""
from __future__ import annotations

import json
import re
from urllib.parse import parse_qsl, urlsplit

_SAFE_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")
_SIGNATURE_NAMES = frozenset({
    "sign", "sig", "signature", "hmac", "checksum", "xsign", "xsignature",
})
_MAX_BODY_BYTES = 128 * 1024
_MAX_SCAN_ITEMS = 64
_MAX_INDICATORS = 12


def _signature_name(name: object) -> bool:
    if not isinstance(name, str) or not _SAFE_NAME.fullmatch(name):
        return False
    normalized = re.sub(r"[^a-z0-9]", "", name.lower())
    return normalized in _SIGNATURE_NAMES or normalized.endswith("signature")


def observed_signature_fields(
    headers: dict | None,
    url: str,
    post_data: str | None = None,
) -> list[str]:
    """Return bounded labels like 'header:x-signature'; never request values."""
    markers: set[str] = set()

    for name in (headers or {}):
        if _signature_name(name):
            markers.add(f"header:{name.lower()}")

    try:
        for name, _ in parse_qsl(urlsplit(url).query, keep_blank_values=True)[:_MAX_SCAN_ITEMS]:
            if _signature_name(name):
                markers.add(f"query:{name.lower()}")
    except (TypeError, ValueError):
        pass

    if isinstance(post_data, str) and len(post_data) <= _MAX_BODY_BYTES:
        try:
            payload = json.loads(post_data)
        except (ValueError, TypeError):
            payload = None
            try:
                for name, _ in parse_qsl(post_data, keep_blank_values=True)[:_MAX_SCAN_ITEMS]:
                    if _signature_name(name):
                        markers.add(f"body:{name.lower()}")
            except (TypeError, ValueError):
                pass

        seen = 0

        def walk(node: object, names: tuple[str, ...] = ()) -> None:
            nonlocal seen
            if seen >= _MAX_SCAN_ITEMS or len(names) >= 4:
                return
            if isinstance(node, dict):
                for key, value in node.items():
                    if seen >= _MAX_SCAN_ITEMS:
                        break
                    seen += 1
                    if not isinstance(key, str) or not _SAFE_NAME.fullmatch(key):
                        continue
                    trail = (*names, key.lower())
                    if _signature_name(key):
                        markers.add("body:" + ".".join(trail))
                    if isinstance(value, (dict, list)):
                        walk(value, trail)
            elif isinstance(node, list):
                for item in node[:3]:
                    if seen >= _MAX_SCAN_ITEMS:
                        break
                    walk(item, names)

        walk(payload)

    return sorted(markers)[:_MAX_INDICATORS]
