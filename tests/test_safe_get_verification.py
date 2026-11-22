"""V13 local-only explicit GET verification; all network traffic is mocked."""
import asyncio
import json

import httpx
import pytest

from api_extractor.config import SiteConfig, load_site_config
from api_extractor.jsonl_logger import JsonlLogger
from api_extractor.request_control import RequestGate
from api_extractor.scope import ScopeGuard
from api_extractor.verification import ExplicitGetVerifier
from api_extractor.normalization import normalize_candidates
from api_extractor.evidence import audit_endpoints, split_by_request_proof


URL = "https://app.example.com/api/items"


def fixture(tmp_path, allow=None, transport=None):
    config = SiteConfig("local", "https://app.example.com/", ["app.example.com"], [], {},
                        explicit_readonly_get_urls=allow or [])
    logger = JsonlLogger(tmp_path / "tool.log")
    verifier = ExplicitGetVerifier(config, ScopeGuard(config.entry, config.allowed_hosts),
                                  RequestGate(max_rps=1000), logger, tmp_path,
                                  transport=transport)
    return verifier, logger


def source(url=URL, method="GET", kind="ast"):
    return {"url": url, "method": method, "source": kind}


def run(verifier, candidates):
    return asyncio.run(verifier.run(candidates))


def test_default_is_network_silent(tmp_path):
    calls = []
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, json={"ok": True})
    verifier, logger = fixture(tmp_path, transport=httpx.MockTransport(handler))
    try:
        assert run(verifier, [source()]) == []
        assert calls == []
        assert json.loads((tmp_path / "evidence/probe.har").read_text())["log"]["entries"] == []
    finally:
        logger.close()


def test_successful_json_get_has_correlated_har_and_log(tmp_path):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"id": 2})
    verifier, logger = fixture(tmp_path, [URL], httpx.MockTransport(handler))
    try:
        observed = run(verifier, [source()])
        assert len(observed) == 1 and observed[0]["source"] == "verified_get"
        assert calls[0].method == "GET"
        assert "authorization" not in calls[0].headers and "cookie" not in calls[0].headers
        assert calls[0].headers["accept"] == "application/json"
        endpoints = normalize_candidates(observed)
        audited, bad, dropped = audit_endpoints(endpoints, tmp_path, logger.start_offset)
        assert bad == dropped == 0
        confirmed, review = split_by_request_proof(audited)
        assert len(confirmed) == 1 and review == []
        assert confirmed[0]["evidence"][0]["file"] == "evidence/probe.har"
        assert json.loads((tmp_path / "evidence/probe.har").read_text())["log"]["entries"][0]["response"]["status"] == 200
    finally:
        logger.close()


def test_unlisted_or_undeclared_never_called(tmp_path):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"ok": True})
    verifier, logger = fixture(tmp_path, [URL], httpx.MockTransport(handler))
    try:
        assert run(verifier, [source("https://app.example.com/api/else")]) == []
        assert calls == []
    finally:
        logger.close()


@pytest.mark.parametrize("url", [
    "https://app.example.com/api/items?token=secret",
    "https://app.example.com/api/{id}",
    "https://app.example.com/api/../admin",
    "https://user:password@app.example.com/api/items",
    "https://app.example.com/api/items#fragment",
    "https://app.example.com/api/%2e%2e/admin",
    "wss://app.example.com/api/items",
    "https://app.example.com/api/a%5Cb",
])
def test_unsafe_or_ambiguous_urls_are_skipped(tmp_path, url):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"ok": True})
    verifier, logger = fixture(tmp_path, [url], httpx.MockTransport(handler))
    try:
        assert run(verifier, [source(url)]) == []
        assert calls == []
    finally:
        logger.close()


def test_out_of_scope_never_requested(tmp_path):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"ok": True})
    url = "https://other.example.com/api/items"
    verifier, logger = fixture(tmp_path, [url], httpx.MockTransport(handler))
    try:
        assert run(verifier, [source(url)]) == []
        assert not calls
    finally:
        logger.close()


@pytest.mark.parametrize("status,content_type", [
    (200, "text/html"), (302, "application/json"), (404, "application/json"),
    (200, "text/plain"), (401, "application/json")
])
def test_unverified_status_or_spa_html_does_not_enter_result(tmp_path, status, content_type):
    requests = []
    def handler(req):
        requests.append(req)
        return httpx.Response(status, headers={"content-type": content_type, "location": "https://evil.test/"})
    verifier, logger = fixture(tmp_path, [URL], httpx.MockTransport(handler))
    try:
        assert run(verifier, [source()]) == []
        assert len(requests) == 1
        assert len(json.loads((tmp_path / "evidence/probe.har").read_text())["log"]["entries"]) == 0
    finally:
        logger.close()


def test_post_or_mutating_methods_are_never_probed(tmp_path):
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"ok": True})
    verifier, logger = fixture(tmp_path, [URL], httpx.MockTransport(handler))
    try:
        assert run(verifier, [source(method="POST"), source(method="DELETE")]) == []
        assert calls == []
    finally:
        logger.close()


def test_operator_list_is_bounded_by_config(tmp_path):
    cfg = tmp_path / "site.json"
    cfg.write_text(json.dumps({"explicit_readonly_get_urls": [URL] * 6}))
    with pytest.raises(ValueError):
        load_site_config(cfg)


def test_probe_har_does_not_depend_on_previous_log_or_har(tmp_path):
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"ok": True})
    verifier, logger = fixture(tmp_path, [URL], httpx.MockTransport(handler))
    try:
        run(verifier, [source()])
        assert len(json.loads((tmp_path / "evidence/probe.har").read_text())["log"]["entries"]) == 1
        verifier.config.explicit_readonly_get_urls = []
        run(verifier, [source()])
        assert json.loads((tmp_path / "evidence/probe.har").read_text())["log"]["entries"] == []
        assert len(calls) == 1
    finally:
        logger.close()


def test_default_site_config_preserves_original_contract(tmp_path):
    cfg = tmp_path / "site.json"
    cfg.write_text(json.dumps({"site_id": "s", "allowed_hosts": ["app.example.com"]}))
    assert load_site_config(cfg).explicit_readonly_get_urls == []
