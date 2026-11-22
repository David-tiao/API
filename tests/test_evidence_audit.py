import json
from pathlib import Path

from api_extractor.evidence import audit_endpoints


def endpoint(method="GET", path="/api/items", evidence=None):
    return {"method": method, "path": path, "host": "app.example.com",
            "evidence": evidence or []}


def test_static_evidence_exists_and_matches_excerpt(tmp_path):
    js = tmp_path / "evidence" / "js" / "main.js"
    js.parent.mkdir(parents=True)
    js.write_text('fetch("/api/items")', encoding="utf-8")
    original = endpoint(evidence=[{"type": "bundle", "file": "evidence/js/main.js",
                                   "snippet": 'fetch("/api/items")'}])
    audited, bad, dropped = audit_endpoints([original], tmp_path)
    assert audited == [original]
    assert (bad, dropped) == (0, 0)


def test_missing_file_traversal_and_symlink_are_dropped(tmp_path):
    outside = tmp_path.parent / "outside.js"
    outside.write_text("secret")
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence" / "link.js").symlink_to(outside)
    rows = [endpoint(evidence=[{"type": "bundle", "file": f}]) for f in (
        "evidence/missing.js", "../outside.js", "evidence/link.js")]
    audited, bad, dropped = audit_endpoints(rows, tmp_path)
    assert audited == []
    assert (bad, dropped) == (3, 3)


def write_har(tmp_path, url="https://app.example.com/api/items", method="GET", kind="xhr", idx=0):
    p = tmp_path / "evidence" / "dynamic.har"
    p.parent.mkdir(exist_ok=True)
    status = 101 if kind == "websocket" else 200
    p.write_text(json.dumps({"log": {"entries": [{"request": {
        "method": method, "url": url}, "response": {"status": status},
        "_resourceType": kind, "_requestIndex": idx}]}}))
    (tmp_path / "tool.log").write_text(json.dumps({"method": method, "url": url,
        "phase": "dynamic", "status": status, "request_index": idx}) + "\n")
    return {"type": "har", "file": "evidence/dynamic.har", "request_index": idx}


def test_har_matches_request_method_host_path_and_log(tmp_path):
    evidence = write_har(tmp_path)
    valid = endpoint(evidence=[evidence])
    wrong = endpoint(method="POST", evidence=[evidence])
    out, bad, dropped = audit_endpoints([valid, wrong], tmp_path)
    assert out == [valid]
    assert (bad, dropped) == (1, 1)


def test_har_index_mismatch_is_rejected(tmp_path):
    evidence = write_har(tmp_path, idx=0)
    evidence["request_index"] = 4
    out, bad, dropped = audit_endpoints([endpoint(evidence=[evidence])], tmp_path)
    assert not out and (bad, dropped) == (1, 1)


def test_missing_request_log_is_rejected(tmp_path):
    evidence = write_har(tmp_path)
    (tmp_path / "tool.log").unlink()
    assert audit_endpoints([endpoint(evidence=[evidence])], tmp_path)[0] == []


def test_valid_static_evidence_survives_bad_har(tmp_path):
    js = tmp_path / "evidence" / "js" / "main.js"
    js.parent.mkdir(parents=True)
    js.write_text("request('/api/items')")
    ep = endpoint(evidence=[{"type": "har", "file": "evidence/none.har", "request_index": 0},
                            {"type": "bundle", "file": "evidence/js/main.js"}])
    out, bad, dropped = audit_endpoints([ep], tmp_path)
    assert len(out) == 1 and len(out[0]["evidence"]) == 1
    assert (bad, dropped) == (1, 0)


def test_websocket_and_graphql_har_map_to_wire_method(tmp_path):
    evidence = write_har(tmp_path, url="wss://app.example.com/stream", method="GET", kind="websocket")
    ws = endpoint(method="WS", path="/stream", evidence=[evidence])
    assert audit_endpoints([ws], tmp_path)[0] == [ws]
    evidence = write_har(tmp_path, url="https://app.example.com/graphql", method="POST", kind="fetch")
    gql = endpoint(method="GQL", path="/graphql", evidence=[evidence])
    assert audit_endpoints([gql], tmp_path)[0] == [gql]
