"""Conservative, bounded GraphQL request classification without exporting values."""
from __future__ import annotations

import json
import re
from urllib.parse import parse_qsl, urlsplit

_MAX_REQUEST_BYTES = 128 * 1024
_MAX_OPERATIONS = 5
_MAX_VARIABLES = 32
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}\Z")
_LEADING_OPERATION = re.compile(
    r"\A\s*(query|mutation|subscription)\b(?:\s+([A-Za-z_][A-Za-z0-9_]{0,63}))?",
    re.I,
)


def _document_operation(value: object) -> tuple[str | None, str | None]:
    if not isinstance(value, str) or len(value) > _MAX_REQUEST_BYTES:
        return None, None
    document = value.lstrip()
    for _ in range(12):
        if not document.startswith("#"):
            break
        newline = document.find("\n")
        if newline < 0:
            return None, None
        document = document[newline + 1:].lstrip()
    if document.startswith("{"):
        return ("query", None) if "}" in document[1:] else (None, None)
    match = _LEADING_OPERATION.match(document)
    if not match or "{" not in document[match.end():]:
        return None, None
    name = match.group(2)
    return match.group(1).lower(), name if name and _IDENTIFIER.fullmatch(name) else None


def _read_payload(post_data: object) -> list[dict]:
    if not isinstance(post_data, str) or len(post_data) > _MAX_REQUEST_BYTES:
        return []
    try:
        data = json.loads(post_data)
    except (ValueError, TypeError):
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [row for row in data[:_MAX_OPERATIONS] if isinstance(row, dict)]
    return []


def _persisted(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    query = value.get("persistedQuery")
    return (isinstance(query, dict)
            and isinstance(query.get("sha256Hash"), str)
            and bool(re.fullmatch(r"[A-Fa-f0-9]{64}", query["sha256Hash"])))


def _url_operations(url: str) -> list[dict]:
    if not isinstance(url, str) or len(url) > _MAX_REQUEST_BYTES:
        return []
    try:
        values = dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))
    except (TypeError, ValueError):
        return []
    row: dict = {}
    if "query" in values:
        row["query"] = values["query"]
    if "operationName" in values:
        row["operationName"] = values["operationName"]
    if "extensions" in values:
        try:
            row["extensions"] = json.loads(values["extensions"][:_MAX_REQUEST_BYTES])
        except (ValueError, TypeError):
            pass
    return [row] if row else []


def _is_graphql_path(url: str) -> bool:
    try:
        segments = [part.lower() for part in urlsplit(url).path.rstrip("/").split("/") if part]
    except (TypeError, ValueError):
        return False
    return bool(segments and segments[-1] in {"graphql", "gql"})


def _raw_document_operation(post_data: object) -> tuple[str | None, str | None]:
    if not isinstance(post_data, str) or len(post_data) > _MAX_REQUEST_BYTES:
        return None, None
    try:
        json.loads(post_data)
    except (TypeError, ValueError):
        return _document_operation(post_data)
    return None, None


def is_raw_graphql_document(post_data: object) -> bool:
    return _raw_document_operation(post_data)[0] is not None


def is_graphql_request(url: str, post_data: object = None) -> bool:
    """A generic REST body such as {"query":"shoes"} is not GraphQL."""
    if _is_graphql_path(url):
        return True
    for row in (*_read_payload(post_data), *_url_operations(url)):
        if _document_operation(row.get("query"))[0] or _persisted(row.get("extensions")):
            return True
    return _raw_document_operation(post_data)[0] is not None


def operation_note(url: str, post_data: object = None) -> str:
    """Return only validated operation identifiers, never query text or variables."""
    for row in (*_read_payload(post_data), *_url_operations(url)):
        kind, name = _document_operation(row.get("query"))
        if kind:
            preferred = row.get("operationName")
            if isinstance(preferred, str) and _IDENTIFIER.fullmatch(preferred):
                name = preferred
            return f"GraphQL {kind} {name} observed" if name else f"GraphQL {kind} observed"
        if _persisted(row.get("extensions")):
            return "GraphQL persisted query observed"
    kind, name = _raw_document_operation(post_data)
    if kind:
        return f"GraphQL {kind} {name} observed" if name else f"GraphQL {kind} observed"
    return "GraphQL endpoint observed"


def _value_type(value: object) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        if value.lower() in {"true", "false"}:
            return "boolean"
        if value.isdecimal():
            return "integer"
    return "string"


def observed_variable_types(post_data: object) -> list[tuple[str, str]]:
    """Return bounded variable names/types without retaining raw values."""
    result: dict[str, str] = {}
    for row in _read_payload(post_data):
        variables = row.get("variables")
        if not isinstance(variables, dict):
            continue
        for name, value in variables.items():
            if len(result) >= _MAX_VARIABLES:
                break
            if isinstance(name, str) and _IDENTIFIER.fullmatch(name):
                result.setdefault(name, _value_type(value))
    return sorted(result.items())
