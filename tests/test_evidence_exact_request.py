"""R6 evidence must identify the same concrete request, not only its path class."""
import json
import pytest

from api_extractor.evidence import audit_endpoints


def exercise(tmp_path, har_url, log_url, *, endpoint_method="GET",
             wire_method="GET", resource_type="fetch", status=200):
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    har = {
        "log": {"entries": [{
            "request": {"method": wire_method, "url": har_url},
            "response": {"status": status},
            "_requestIndex": 0,
            "_resourceType": resource_type,
        }]}
    }
    (evidence_dir / "dynamic.har").write_text(json.dumps(har), encoding="utf-8")
    (tmp_path / "tool.log").write_text(json.dumps({
        "phase": "dynamic", "method": wire_method, "url": log_url,
        "status": status, "request_index": 0,
    }) + "\n", encoding="utf-8")
    endpoint = {
        "method": endpoint_method, "host": "app.example.com",
        "path": "/api/users/{id}" if endpoint_method == "GET" else "/graphql",
        "evidence": [{"type": "har", "file": "evidence/dynamic.har", "request_index": 0}],
    }
    if endpoint_method == "WS":
        endpoint["path"] = "/stream"
    rows, bad, dropped = audit_endpoints([endpoint], tmp_path)
    return rows, bad, dropped


def test_exact_same_request_is_valid(tmp_path):
    url = "https://app.example.com/api/users/123?page=2"
    rows, bad, dropped = exercise(tmp_path, url, url)
    assert len(rows) == 1 and bad == 0 and dropped == 0


@pytest.mark.parametrize("log_url", [
    "https://app.example.com/api/users/456?page=2",
    "https://app.example.com/api/users/123?page=3",
    "http://app.example.com/api/users/123?page=2",
    "https://app.example.com:8443/api/users/123?page=2",
])
def test_similar_but_not_identical_request_is_rejected(tmp_path, log_url):
    har_url = "https://app.example.com/api/users/123?page=2"
    rows, bad, dropped = exercise(tmp_path, har_url, log_url)
    assert rows == [] and bad == 1 and dropped == 1


def test_graphql_post_uses_real_http_method_for_request_proof(tmp_path):
    url = "https://app.example.com/graphql"
    rows, bad, dropped = exercise(tmp_path, url, url, endpoint_method="GQL",
                                   wire_method="POST")
    assert len(rows) == 1 and bad == 0 and dropped == 0


def test_websocket_handshake_requires_matching_get_record(tmp_path):
    url = "wss://app.example.com/stream"
    rows, bad, dropped = exercise(tmp_path, url, url, endpoint_method="WS",
                                   wire_method="GET", resource_type="websocket", status=101)
    assert len(rows) == 1 and bad == 0 and dropped == 0


def test_websocket_wrong_wire_url_is_rejected(tmp_path):
    rows, bad, dropped = exercise(
        tmp_path, "wss://app.example.com/stream", "ws://app.example.com/stream",
        endpoint_method="WS", wire_method="GET", resource_type="websocket", status=101)
    assert rows == [] and bad == 1 and dropped == 1
