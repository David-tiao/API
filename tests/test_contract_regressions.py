"""Regressions for scope, API false positives, and error propagation."""
import asyncio
import json
import pytest

from api_extractor.pipeline import run_pipeline
from api_extractor.scope import ScopeGuard
from api_extractor.normalization import normalize_candidates
from api_extractor.static_analysis import StaticAnalyzer
from api_extractor.crawler import ScriptRecord, ResourceCrawler


def test_default_scope_does_not_authorize_sibling_domains():
    guard = ScopeGuard("https://app.example.com/")
    assert guard.is_allowed("https://app.example.com/api")
    assert guard.is_allowed("https://x.app.example.com/api")
    assert not guard.is_allowed("https://api.example.com/api")
    assert not guard.is_allowed("https://app.example.com.evil.org/api")


def test_explicit_allowlist_may_authorize_sibling_within_site():
    guard = ScopeGuard("https://app.s3.lab/", ["app.s3.lab", "api.s3.lab"])
    assert guard.is_allowed("https://api.s3.lab/api")
    assert not guard.is_allowed("https://api.external.lab/api")


def test_failed_browser_request_does_not_become_endpoint():
    candidates = [
        {"source": "dynamic", "method": "GET", "url": "https://app.example.com/api/no",
         "status": -1, "request_index": 0},
        {"source": "dynamic", "method": "GET", "url": "https://app.example.com/api/missing",
         "status": 404, "request_index": 1},
        {"source": "dynamic", "method": "GET", "url": "https://app.example.com/api/private",
         "status": 401, "request_index": 2},
        {"source": "dynamic", "method": "GET", "url": "https://app.example.com/api/ok",
         "status": 200, "request_index": 3},
    ]
    assert [x["path"] for x in normalize_candidates(candidates)] == ["/api/ok", "/api/private"]


def test_regex_fallback_drops_static_files(tmp_path):
    guard = ScopeGuard("https://app.example.com/")
    analyzer = StaticAnalyzer(tmp_path, tmp_path, guard)
    record = ScriptRecord("https://app.example.com/main.js",
                          'fetch("/images/logo.png"); fetch("/api/users");')
    endpoints, _ = analyzer._regex_fallback(record)
    assert [x["url"] for x in endpoints] == ["https://app.example.com/api/users"]


def test_pipeline_reports_failure_when_crawler_crashes(tmp_path, monkeypatch):
    async def broken_crawl(self):
        raise RuntimeError("simulated crawler failure")
    monkeypatch.setattr(ResourceCrawler, "crawl", broken_crawl)
    cfg = tmp_path / "site.json"
    cfg.write_text(json.dumps({"site_id": "test", "allowed_hosts": ["app.example.com"]}))
    out = tmp_path / "result.json"
    status = asyncio.run(run_pipeline("https://app.example.com/", str(cfg), str(out), 3))
    assert status != 0
    assert json.loads(out.read_text())["endpoints"] == []
    assert "pipeline_error:RuntimeError" in (tmp_path / "tool.log").read_text()


def test_pipeline_rejects_outside_output_before_write(tmp_path, monkeypatch):
    import api_extractor.pipeline as pipeline
    def fail_mount(config, output):
        raise ValueError("invalid /out path")
    monkeypatch.setattr(pipeline, "_validate_mount_paths", fail_mount)
    target = tmp_path / "forbidden" / "result.json"
    with pytest.raises(ValueError):
        asyncio.run(run_pipeline("https://app.example.com/", "ignored", str(target), 3))
    assert not target.parent.exists()


def test_signature_in_body_detected_without_leaking_values():
    from api_extractor.normalization import infer_auth
    body = '{"signature":"secret-value","nonce":"n1"}'
    assert infer_auth({}, 'https://app.example.com/api/order', body) == 'sign'
    assert infer_auth({'X-Design-Theme': 'dark'}, 'https://app.example.com/api/order') == 'none'
    ep = normalize_candidates([{'source': 'dynamic', 'method': 'POST', 'status': 200,
        'url': 'https://app.example.com/api/order', 'post_data': body, 'request_index': 0}])[0]
    assert ep['auth'] == 'sign'
    assert all('secret-value' not in str(v) for v in ep.values())


def test_websocket_and_sse_static_apis_are_discovered(tmp_path):
    guard = ScopeGuard('https://app.example.com/')
    analyzer = StaticAnalyzer(tmp_path, tmp_path, guard)
    record = ScriptRecord('https://app.example.com/app.js',
        'fetch("/api/items"); new WebSocket("wss://app.example.com/live"); new EventSource("/stream");')
    rows, _ = analyzer._regex_fallback(record)
    observed = {(row['method'], row['url']) for row in rows}
    assert ('GET', 'https://app.example.com/api/items') in observed
    assert ('WS', 'wss://app.example.com/live') in observed
    assert ('GET', 'https://app.example.com/stream') in observed


def test_websocket_cannot_escape_target_scope(tmp_path):
    guard = ScopeGuard('https://app.example.com/')
    analyzer = StaticAnalyzer(tmp_path, tmp_path, guard)
    record = ScriptRecord('https://app.example.com/app.js',
        'new WebSocket("wss://other.example.com/live");')
    rows, _ = analyzer._regex_fallback(record)
    assert not rows
