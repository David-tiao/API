"""V13 full pipeline proof check; all HTTP verification uses MockTransport."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import httpx

from api_extractor.crawler import ScriptRecord
from api_extractor.dynamic_analysis import DynamicAnalyzer
from api_extractor.pipeline import run_pipeline
from api_extractor.verification import ExplicitGetVerifier


class FakeCrawler:
    def __init__(self, target, config, guard, gate, logger, out_dir):
        self.target = target
        self.out_dir = Path(out_dir)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def crawl(self):
        path = self.out_dir / "evidence/js/app.js"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('fetch("/api/items")')
        return SimpleNamespace(
            scripts=[ScriptRecord(self.target + "app.js", path.read_text(), "evidence/js/app.js")],
            pages=[], links=[], forms=[])


def test_explicit_json_get_promotes_static_hint_to_verified_result(tmp_path, monkeypatch):
    url = "https://app.example.com/api/items"
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"id": 1})

    monkeypatch.setattr("api_extractor.pipeline.ResourceCrawler", FakeCrawler)
    async def no_browser(self, pages):
        return []
    monkeypatch.setattr(DynamicAnalyzer, "run", no_browser)
    monkeypatch.setattr("api_extractor.pipeline.ExplicitGetVerifier",
                        lambda *args: ExplicitGetVerifier(*args, transport=httpx.MockTransport(handler)))
    cfg = tmp_path / "site.json"
    cfg.write_text(json.dumps({"site_id": "local", "allowed_hosts": ["app.example.com"],
                              "explicit_readonly_get_urls": [url]}))
    target = tmp_path / "result.json"
    result_code = asyncio.run(run_pipeline("https://app.example.com/", str(cfg), str(target), 10))
    result = json.loads(target.read_text())
    assert result_code == 0
    assert len(requests) == 1 and requests[0].method == "GET"
    assert [(e["method"], e["path"]) for e in result["endpoints"]] == [("GET", "/api/items")]
    assert {e["file"] for e in result["endpoints"][0]["evidence"]} == {
        "evidence/js/" + next((tmp_path / "evidence/js").iterdir()).name,
        "evidence/probe.har",
    }
    assert json.loads((tmp_path / "static_candidates.json").read_text())["candidates"] == []
    log = (tmp_path / "tool.log").read_text()
    assert '"phase": "probe"' in log and '"status": 200' in log
    assert "request_proof_gate:confirmed=1,static_only=0" in log


def test_off_by_default_does_not_probe_at_pipeline_level(tmp_path, monkeypatch):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"ok": True})
    monkeypatch.setattr("api_extractor.pipeline.ResourceCrawler", FakeCrawler)
    async def no_browser(self, pages):
        return []
    monkeypatch.setattr(DynamicAnalyzer, "run", no_browser)
    monkeypatch.setattr("api_extractor.pipeline.ExplicitGetVerifier",
                        lambda *args: ExplicitGetVerifier(*args, transport=httpx.MockTransport(handler)))
    cfg = tmp_path / "site.json"
    cfg.write_text(json.dumps({"site_id": "local", "allowed_hosts": ["app.example.com"]}))
    target = tmp_path / "result.json"
    result_code = asyncio.run(run_pipeline("https://app.example.com/", str(cfg), str(target), 10))
    assert result_code == 0
    assert requests == []
    assert json.loads(target.read_text())["endpoints"] == []
    assert len(json.loads((tmp_path / "static_candidates.json").read_text())["candidates"]) == 1
