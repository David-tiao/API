from __future__ import annotations

import json
import re
from collections import defaultdict
from urllib.parse import parse_qsl, urlsplit

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


def infer_auth(headers: dict | None, url: str) -> str:
    headers = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
    if any("sign" in k.lower() for k in headers) or any(any(x in k.lower() for x in ("sign", "signature", "timestamp", "nonce")) for k, _ in parse_qsl(urlsplit(url).query)):
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
    for candidate in candidates:
        url = str(candidate.get("url") or "")
        parsed = urlsplit(url)
        if not parsed.hostname or parsed.scheme not in {"http", "https", "ws", "wss"}:
            continue
        method = str(candidate.get("method") or "GET").upper()
        if method != "WS" and ("graphql" in parsed.path.lower() or (candidate.get("post_data") and any(x in str(candidate.get("post_data")).lower() for x in ("\"query\"", "mutation ", "query ")))):
            method = "GQL"
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "WS", "GQL"}:
            continue
        path = normalize_path(parsed.path)
        host = parsed.hostname.lower()
        key = (method, host, path)
        query = [_field(k, v, False) for k, v in parse_qsl(parsed.query, keep_blank_values=True)]
        body = _body_fields(candidate.get("post_data"))
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
        elif source == "dynamic":
            evidence.append({"type": "har", "file": "evidence/dynamic.har", "request_index": int(candidate.get("request_index", 0))})
        if not evidence:
            continue

        entry = merged.get(key)
        if not entry:
            entry = {
                "method": method,
                "path": path,
                "host": host,
                "auth": infer_auth(candidate.get("headers"), url),
                "params": {"path": path_params, "query": _merge_fields(query), "body": _merge_fields(body)},
                "evidence": [],
                "confidence": float(candidate.get("confidence", 0.5)),
                "note": candidate.get("note") or infer_note(path),
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
            new_auth = infer_auth(candidate.get("headers"), url)
            if new_auth != "none":
                entry["auth"] = new_auth
            if candidate.get("response_content_type") or candidate.get("response_fields"):
                entry["response"] = {
                    "content_type": candidate.get("response_content_type") or "application/octet-stream",
                    "fields": list(dict.fromkeys(candidate.get("response_fields") or []))[:100],
                }
            if candidate.get("note"):
                entry["note"] = candidate["note"]
        for item in evidence:
            if item not in entry["evidence"]:
                entry["evidence"].append(item)

    return sorted(merged.values(), key=lambda x: (x["host"], x["path"], x["method"]))
