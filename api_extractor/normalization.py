from __future__ import annotations

import json
import re
from collections import defaultdict
from urllib.parse import parse_qsl, urlsplit

from .signature_semantics import observed_signature_fields
from .transport_semantics import socketio_transport_note
from .graphql_semantics import (
    is_graphql_request, is_raw_graphql_document, operation_note, observed_variable_types,
)

_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$")
_LONG_HEX = re.compile(r"^[0-9a-fA-F]{16,}$")
_NUMERIC = re.compile(r"^\d+$")
_SENSITIVE = ("token", "secret", "password", "passwd", "authorization", "api_key", "apikey", "signature", "sign", "session", "cookie")


def infer_type(value) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, (dict, list)):
        return "object" if isinstance(value, dict) else "array"
    if isinstance(value, str):
        if value.lower() in {"true", "false"}:
            return "boolean"
        if _NUMERIC.match(value):
            return "integer"
    return "string"


def normalize_path(path: str) -> str:
    path = path or "/"
    if not path.startswith("/"):
        path = "/" + path
    segments = []
    for segment in path.split("/"):
        if not segment:
            continue
        if segment.startswith(":") or (segment.startswith("{") and segment.endswith("}")):
            name = segment.strip(":{}").strip() or "id"
            segments.append("{" + name + "}")
        elif _UUID.match(segment) or _NUMERIC.match(segment) or _LONG_HEX.match(segment):
            segments.append("{id}")
        else:
            segments.append(segment)
    return "/" + "/".join(segments)


def _field(name: str, value=None, required: bool = False, fallback_type: str | None = None) -> dict:
    return {"name": str(name), "type": fallback_type or infer_type(value), "required": bool(required)}


def _body_fields(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        payload = json.loads(raw)
        if isinstance(payload, dict):
            return [_field(k, v, True) for k, v in payload.items()]
        if isinstance(payload, list) and payload and isinstance(payload[0], dict):
            return [_field(k, v, False) for k, v in payload[0].items()]
    except Exception:
        pass
    try:
        return [_field(k, v, True) for k, v in parse_qsl(raw, keep_blank_values=True)]
    except Exception:
        return []


def _merge_fields(*groups: list[dict]) -> list[dict]:
    merged = {}
    for group in groups:
        for item in group or []:
            name = str(item.get("name") or "")
            if not name:
                continue
            previous = merged.get(name)
            if previous:
                previous["required"] = bool(previous.get("required") or item.get("required"))
                if previous.get("type") == "string" and item.get("type") != "string":
                    previous["type"] = item.get("type")
            else:
                merged[name] = {"name": name, "type": item.get("type") or "string", "required": bool(item.get("required", False))}
    return [merged[key] for key in sorted(merged)]


def _is_signature_key(name: str) -> bool:
    # Avoid treating unrelated words such as "design" as a cryptographic signature.
    normalized = re.sub(r"[^a-z0-9]", "", name.lower())
    return normalized in {"sign", "signature", "sig", "hmac", "xsign", "xsignature", "checksum"} or normalized.endswith("signature")


def infer_auth(headers: dict | None, url: str, post_data: str | None = None) -> str:
    headers = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
    signed = any(_is_signature_key(k) for k in headers)
    signed |= any(_is_signature_key(k) for k, _ in parse_qsl(urlsplit(url).query))
    if post_data:
        try:
            data = json.loads(post_data)
            keys = data.keys() if isinstance(data, dict) else ()
        except (ValueError, TypeError):
            keys = (k for k, _ in parse_qsl(post_data, keep_blank_values=True))
        signed |= any(_is_signature_key(str(k)) for k in keys)
    if signed:
        return "sign"
    if "authorization" in headers:
        value = headers["authorization"].lower()
        if value.startswith("bearer "):
            return "bearer"
        return "apikey"
    if any(x in k for k in headers for x in ("x-api-key", "api-key", "apikey")):
        return "apikey"
    if "cookie" in headers:
        return "cookie"
    query_keys = [k.lower() for k, _ in parse_qsl(urlsplit(url).query)]
    if any(any(s in k for s in _SENSITIVE) for k in query_keys):
        return "apikey"
    return "none"


def infer_note(path: str) -> str:
    tokens = [x for x in path.strip("/").split("/") if x and not x.startswith("{")]
    tokens = [x for x in tokens if x.lower() not in {"api", "v1", "v2", "v3", "rest", "graphql"}]
    if not tokens:
        return "Backend endpoint observed; business purpose is not yet clear"
    subject = tokens[-1].replace("-", " ").replace("_", " ")
    subject = re.sub(r"\{.*?\}", "resource", subject).strip()
    return f"Potential {subject or 'resource'} operation inferred from the request path"


def normalize_candidates(candidates: list[dict]) -> list[dict]:
    merged: dict[tuple[str, str, str], dict] = {}
    signed_observations: dict[tuple[str, str, str], set[str]] = {}
    for candidate in candidates:
        # Failed/unfinished browser requests are not proof that an API exists.
        # Static candidates do not have an HTTP status by definition.
        if candidate.get("source") in {"dynamic", "verified_get"}:
            status = candidate.get("status")
            if status is not None:
                try:
                    code = int(status)
                except (TypeError, ValueError):
                    continue
                if code < 100 or (code >= 400 and code not in {401, 403}):
                    continue
        url = str(candidate.get("url") or "")
        parsed = urlsplit(url)
        if not parsed.hostname or parsed.scheme not in {"http", "https", "ws", "wss"}:
            continue
        method = str(candidate.get("method") or "GET").upper()
        # Preserve observed HTTP method when the browser's older heuristic
        # mislabeled an ordinary JSON search request as GraphQL.
        if method == "GQL" and candidate.get("http_method"):
            method = str(candidate["http_method"]).upper()
        if method != "WS" and is_graphql_request(url, candidate.get("post_data")):
            method = "GQL"
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "WS", "GQL"}:
            continue
        path = normalize_path(parsed.path)
        host = parsed.hostname.lower()
        key = (method, host, path)
        transport_note = (
            socketio_transport_note(url, method, candidate.get("resource_type"))
            if candidate.get("source") == "dynamic" else None
        )
        query = [_field(k, v, False) for k, v in parse_qsl(parsed.query, keep_blank_values=True)]
        if transport_note:
            # Engine.IO frames are opaque; treating them as form-encoded
            # fields would export private message payload as parameter names.
            body = []
        elif method == "GQL" and is_raw_graphql_document(candidate.get("post_data")):
            # Raw GraphQL query text must never become a form field *name*.
            body = [_field("query", None, True, "string")]
        else:
            body = _body_fields(candidate.get("post_data"))
        if method == "GQL":
            body.extend(
                _field("variables." + name, None, False, fallback_type=field_type)
                for name, field_type in observed_variable_types(candidate.get("post_data"))
            )
        body.extend(_field(name, None, False) for name in candidate.get("body_fields", []))
        query.extend(_field(name, None, False) for name in candidate.get("query_fields", []))
        path_params = []
        for segment in path.split("/"):
            if segment.startswith("{") and segment.endswith("}"):
                path_params.append(_field(segment[1:-1], None, True, "string"))
        evidence = []
        source = candidate.get("source")
        if source in {"ast", "regex", "html"}:
            evidence.append({
                "type": "bundle" if source in {"ast", "regex"} else "html",
                "file": candidate.get("file") or "evidence/unknown",
                "loc": f"line {candidate.get('line')}" if candidate.get("line") else "captured from page markup",
                "snippet": (candidate.get("snippet") or "")[:300],
            })
        elif source in {"dynamic", "verified_get"}:
            evidence.append({"type": "har", "file": candidate.get("evidence_file") or "evidence/dynamic.har", "request_index": int(candidate.get("request_index", 0))})
        if not evidence:
            continue

        # Only an actual observed request can support signing metadata.
        signature_labels = (
            observed_signature_fields(candidate.get("headers"), url, candidate.get("post_data"))
            if source in {"dynamic", "verified_get"} and not transport_note else []
        )
        if signature_labels:
            signed_observations.setdefault(key, set()).update(signature_labels)

        entry = merged.get(key)
        if not entry:
            entry = {
                "method": method,
                "path": path,
                "host": host,
                "auth": ("sign" if signature_labels else
                         infer_auth(candidate.get("headers"), url,
                                    None if transport_note else candidate.get("post_data"))),
                "params": {"path": path_params, "query": _merge_fields(query), "body": _merge_fields(body)},
                "evidence": [],
                "confidence": float(candidate.get("confidence", 0.5)),
                "note": (transport_note or
                         (operation_note(url, candidate.get("post_data")) if method == "GQL"
                          else candidate.get("note") or infer_note(path))),
            }
            if candidate.get("response_content_type") or candidate.get("response_fields"):
                entry["response"] = {
                    "content_type": candidate.get("response_content_type") or "application/octet-stream",
                    "fields": list(dict.fromkeys(candidate.get("response_fields") or []))[:100],
                }
            merged[key] = entry
        else:
            entry["confidence"] = max(float(entry.get("confidence", 0)), float(candidate.get("confidence", 0.5)))
            entry["params"]["query"] = _merge_fields(entry["params"]["query"], query)
            entry["params"]["body"] = _merge_fields(entry["params"]["body"], body)
            entry["params"]["path"] = _merge_fields(entry["params"]["path"], path_params)
            new_auth = infer_auth(candidate.get("headers"), url,
                                  None if transport_note else candidate.get("post_data"))
            if new_auth == "sign" or (new_auth != "none" and entry["auth"] != "sign"):
                entry["auth"] = new_auth
            if candidate.get("response_content_type") or candidate.get("response_fields"):
                entry["response"] = {
                    "content_type": candidate.get("response_content_type") or "application/octet-stream",
                    "fields": list(dict.fromkeys(candidate.get("response_fields") or []))[:100],
                }
            if transport_note:
                entry["note"] = transport_note
            elif method == "GQL":
                # Never export untrusted browser note or raw GraphQL content.
                proposed = operation_note(url, candidate.get("post_data"))
                if proposed != "GraphQL endpoint observed":
                    entry["note"] = proposed
            elif candidate.get("note"):
                entry["note"] = candidate["note"]
        for item in evidence:
            if item not in entry["evidence"]:
                entry["evidence"].append(item)

    for key, fields in signed_observations.items():
        if key in merged:
            merged[key]["auth"] = "sign"
            merged[key]["note"] = (
                f"{merged[key]['note']} | Signing fields observed: "
                + ", ".join(sorted(fields)[:12])
                + " (algorithm not reconstructed)"
            )
    return sorted(merged.values(), key=lambda x: (x["host"], x["path"], x["method"]))
