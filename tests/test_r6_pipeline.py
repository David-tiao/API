"""Offline R6 pipeline checks (browser and crawler are fixtures)."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from api_extractor.crawler import ScriptRecord
from api_extractor.dynamic_analysis import DynamicAnalyzer
from api_extractor.pipeline import run_pipeline


class FixtureCrawler:
    emit_script = True

    def __init__(self, target, config, guard, gate, logger, out_dir):
        self.target, self.out_dir = target, Path(out_dir)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def crawl(self):
        if not self.emit_script:
            return SimpleNamespace(scripts=[], pages=[], links=[], forms=[])
        path = self.out_dir / "evidence/js/app.js"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('fetch("/api/items")')
        return SimpleNamespace(
            scripts=[ScriptRecord(self.target + "app.js", path.read_text(), "evidence/js/app.js")],
            pages=[], links=[], forms=[])


def execute(tmp_path, monkeypatch, browser):
    monkeypatch.setattr("api_extractor.pipeline.ResourceCrawler", FixtureCrawler)
    monkeypatch.setattr(DynamicAnalyzer, "run", browser)
    config = tmp_path / "site.json"
    config.write_text(json.dumps({"site_id": "offline", "allowed_hosts": ["app.example.com"]}))
    out = tmp_path / "result.json"
    code = asyncio.run(run_pipeline("https://app.example.com/", str(config), str(out), 5))
    review = json.loads((tmp_path / "static_candidates.json").read_text())
    return code, json.loads(out.read_text()), review, (tmp_path / "tool.log").read_text()


def test_static_only_is_reviewed_without_forged_log(tmp_path, monkeypatch):
    async def no_browser(self, pages):
        return []
    code, result, review, log = execute(tmp_path, monkeypatch, no_browser)
    assert code == 0 and result["endpoints"] == []
    assert [(c["method"], c["path"]) for c in review["candidates"]] == [("GET", "/api/items")]
    assert "request_proof_gate:confirmed=0,static_only=1" in log
    assert '"url": "https://app.example.com/api/items"' not in log


def test_observed_har_and_log_make_endpoint_eligible(tmp_path, monkeypatch):
    async def observed(self, pages):
        url = "https://app.example.com/api/items"
        self.records.append({"url": url, "http_method": "GET", "method": "GET",
                             "status": 200, "resource_type": "fetch", "request_index": 0})
        self.logger.write("GET", url, 200, "dynamic", request_index=0, resource_type="fetch")
        self._write_har()
        return self.records

    code, result, review, log = execute(tmp_path, monkeypatch, observed)
    assert code == 0
    assert [(e["method"], e["path"]) for e in result["endpoints"]] == [("GET", "/api/items")]
    assert {e["type"] for e in result["endpoints"][0]["evidence"]} == {"bundle", "har"}
    assert review["candidates"] == []


def test_unproven_dynamic_without_har_stays_unverified(tmp_path, monkeypatch):
    async def missing_har(self, pages):
        url = "https://app.example.com/api/items"
        self.records.append({"url": url, "method": "GET", "http_method": "GET",
                             "status": 200, "resource_type": "fetch", "request_index": 0})
        self.logger.write("GET", url, 200, "dynamic", request_index=0)
        return self.records

    _, result, review, _ = execute(tmp_path, monkeypatch, missing_har)
    assert result["endpoints"] == [] and len(review["candidates"]) == 1


def test_second_run_clears_previous_review_sidecar(tmp_path, monkeypatch):
    async def no_browser(self, pages):
        return []
    execute(tmp_path, monkeypatch, no_browser)
    assert len(json.loads((tmp_path / "static_candidates.json").read_text())["candidates"]) == 1
    monkeypatch.setattr(FixtureCrawler, "emit_script", False)
    execute(tmp_path, monkeypatch, no_browser)
    assert json.loads((tmp_path / "static_candidates.json").read_text())["candidates"] == []
