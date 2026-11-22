"""R6 proof gate: static declarations are never logged as observed requests."""
import json

from api_extractor.evidence import split_by_request_proof
from api_extractor.output import write_static_review


def endpoint(evidence, path="/api/items", method="GET"):
    return {"method": method, "host": "app.example.test", "path": path,
            "evidence": evidence, "params": {"path": [], "query": [], "body": []},
            "auth": "none"}


def test_only_static_evidence_not_verified():
    static = endpoint([{"type": "bundle", "file": "evidence/js/app.js"}])
    assert split_by_request_proof([static]) == ([], [static])


def test_audited_har_is_request_proof():
    observed = endpoint([{"type": "har", "file": "evidence/dynamic.har", "request_index": 0}])
    assert split_by_request_proof([observed]) == ([observed], [])


def test_static_dynamic_evidence_preserved_together():
    both = endpoint([{"type": "bundle", "file": "evidence/js/app.js"},
                     {"type": "har", "file": "evidence/dynamic.har", "request_index": 1}])
    assert split_by_request_proof([both]) == ([both], [])


def test_sidecar_does_not_duplicate_credentials_or_source_snippets(tmp_path):
    row = endpoint([{"type": "bundle", "file": "evidence/js/app.js",
                    "loc": "line 22", "snippet": 'const token="secret-value";'}])
    row["headers"] = {"Authorization": "secret-value"}
    path = tmp_path / "static_candidates.json"
    write_static_review(path, "site", [row])
    raw = path.read_text()
    assert "secret-value" not in raw
    data = json.loads(raw)
    assert data["kind"] == "unverified_static_candidates"
    assert data["candidates"][0]["sources"] == [
        {"type": "bundle", "file": "evidence/js/app.js", "loc": "line 22"}]


def test_review_sidecar_overwrites_old_results(tmp_path):
    path = tmp_path / "static_candidates.json"
    write_static_review(path, "site", [endpoint([{"type": "html", "file": "page.html"}])])
    write_static_review(path, "site", [])
    assert json.loads(path.read_text())["candidates"] == []
    assert not (tmp_path / "static_candidates.json.tmp").exists()


def test_unproven_empty_evidence_never_enters_main_result():
    unknown = endpoint([])
    assert split_by_request_proof([unknown]) == ([], [unknown])


def test_partition_preserves_order_and_source_data():
    a = endpoint([{"type": "bundle", "file": "a.js"}], "/a")
    b = endpoint([{"type": "har", "file": "dynamic.har", "request_index": 0}], "/b")
    c = endpoint([{"type": "html", "file": "page.html"}], "/c", "POST")
    verified, review = split_by_request_proof([a, b, c])
    assert verified == [b] and review == [a, c]


def test_partition_has_no_network_or_disk_side_effects(tmp_path):
    split_by_request_proof([endpoint([{"type": "bundle", "file": "script.js"}])])
    assert list(tmp_path.iterdir()) == []
