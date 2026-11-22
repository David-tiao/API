"""Pure conversion of collected observations into normalization candidates.

No network, browser, filesystem or global-state side effects: scope validation,
normalization and evidence auditing belong to later pipeline stages.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

_NETWORK_API_RESOURCES = frozenset({"fetch", "xhr", "eventsource", "websocket"})


def from_html_forms(forms: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Convert already-collected HTML form records into API candidates."""
    candidates: list[dict[str, Any]] = []
    for form in forms:
        url = form.get("url")
        if not isinstance(url, str) or not url:
            continue
        field_names = [
            field.get("name") for field in form.get("fields", [])
            if isinstance(field, Mapping)
            and isinstance(field.get("name"), str)
            and field.get("name")
        ]
        candidates.append({
            "method": form.get("method", "GET"),
            "url": url,
            "source": "html",
            "confidence": 0.58,
            "file": form.get("file", ""),
            "body_fields": field_names,
            "note": "Form submission endpoint inferred from HTML",
        })
    return candidates


def from_network_records(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Convert browser observations while excluding documents/static assets.

    Preserve HTTP status and request index for the later evidence auditor.
    A candidate is not automatically proof that the request succeeded.
    """
    candidates: list[dict[str, Any]] = []
    for row in records:
        if row.get("resource_type") not in _NETWORK_API_RESOURCES:
            continue
        url = row.get("url")
        if not isinstance(url, str) or not url:
            continue
        candidates.append({
            "method": row.get("method") or row.get("http_method") or "GET",
            "http_method": row.get("http_method") or row.get("method") or "GET",
            "url": url,
            "source": "dynamic",
            "confidence": 0.96,
            "headers": row.get("headers") or {},
            "post_data": row.get("post_data"),
            "response_content_type": row.get("response_content_type"),
            "response_fields": row.get("response_fields") or [],
            "status": row.get("status"),
            "request_index": row.get("request_index", 0),
            "note": row.get("note"),
        })
    return candidates
