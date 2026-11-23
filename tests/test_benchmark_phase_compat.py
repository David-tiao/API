"""Regression: benchmark reads normalized and historical request phases."""
import json
from api_extractor.offline_benchmark import _observed_log


def test_benchmark_accepts_normalized_probe_and_legacy_probe(tmp_path):
    rows = [
        {"phase": "verify", "detail_phase": "probe", "method": "GET",
         "url": "https://app.example.com/api/items", "status": 200,
         "request_index": 2, "resource_type": "explicit_safe_get"},
        {"phase": "probe", "method": "GET",
         "url": "https://app.example.com/api/legacy", "status": 200,
         "request_index": 3, "resource_type": "explicit_safe_get"},
    ]
    (tmp_path / "tool.log").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    observed = _observed_log(tmp_path)
    assert ("GET", "app.example.com", "/api/items", 2, 200) in observed
    assert ("GET", "app.example.com", "/api/legacy", 3, 200) in observed


def test_benchmark_never_treats_redirect_as_api_proof(tmp_path):
    rows = [
        {"phase": "dynamic", "detail_phase": "redirect", "method": "GET",
         "url": "https://app.example.com/api/redirect-only", "status": 200,
         "request_index": 0},
        {"phase": "verify", "detail_phase": "probe", "method": "GET",
         "url": "https://app.example.com/api/unverified", "status": 200,
         "request_index": 1, "resource_type": "other"},
        {"phase": "dynamic", "method": "GET",
         "url": "https://app.example.com/api/real", "status": 200,
         "request_index": 2},
    ]
    (tmp_path / "tool.log").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    assert _observed_log(tmp_path) == {("GET", "app.example.com", "/api/real", 2, 200)}
