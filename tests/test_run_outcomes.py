"""Offline tests for phase outcomes, R2 exit code and partial evidence retention."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from api_extractor.config import SiteConfig
from api_extractor.crawler import ScriptRecord
from api_extractor.dynamic_analysis import DynamicAnalyzer
from api_extractor.jsonl_logger import JsonlLogger
from api_extractor.pipeline import run_pipeline
from api_extractor.request_control import RequestGate
from api_extractor.scope import ScopeGuard


class StaticFixtureCrawler:
    def __init__(self, target, config, guard, gate, logger, out_dir):
        self.target, self.out_dir = target, Path(out_dir)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def crawl(self):
        path = self.out_dir / "evidence/js/app.js"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('fetch("/api/items")', encoding="utf-8")
        return SimpleNamespace(
            scripts=[ScriptRecord(self.target + "app.js", path.read_text(), "evidence/js/app.js")],
            pages=[], links=[], forms=[])


def run_with_browser(tmp_path, monkeypatch, browser):
    monkeypatch.setattr("api_extractor.pipeline.ResourceCrawler", StaticFixtureCrawler)
    monkeypatch.setattr(DynamicAnalyzer, "run", browser)
    config = tmp_path / "site.json"
    config.write_text(json.dumps({"site_id": "test", "allowed_hosts": ["app.example.com"]}))
    out = tmp_path / "result.json"
    code = asyncio.run(run_pipeline("https://app.example.com/", str(config), str(out), 1))
    return code, json.loads(out.read_text()), (tmp_path / "tool.log").read_text()


def test_dynamic_failure_keeps_verified_static_result(tmp_path, monkeypatch):
    async def failed_browser(self, pages):
        self.failure_reason = "BrowserUnavailable"
        self.logger.write("-", self.target, 0, "dynamic", note="browser_phase_error:BrowserUnavailable")
        return []

    code, data, log = run_with_browser(tmp_path, monkeypatch, failed_browser)
    assert code == 0  # Required by R2 when a valid partial result is available.
    assert [(e["method"], e["path"]) for e in data["endpoints"]] == [("GET", "/api/items")]
    assert "dynamic_phase_failed:BrowserUnavailable" in log
    assert "run_status:partial_browser_failure" in log


def test_budget_timeout_keeps_static_evidence(tmp_path, monkeypatch):
    async def slow_browser(self, pages):
        await asyncio.sleep(60)

    code, data, log = run_with_browser(tmp_path, monkeypatch, slow_browser)
    assert code == 0
    assert [(e["method"], e["path"]) for e in data["endpoints"]] == [("GET", "/api/items")]
    assert "budget_exhausted_partial_results_preserved" in log
    assert "run_status:incomplete_budget" in log


def test_browser_failed_without_valid_api_is_hard_failure(tmp_path, monkeypatch):
    class EmptyCrawler(StaticFixtureCrawler):
        async def crawl(self):
            return SimpleNamespace(scripts=[], pages=[], links=[], forms=[])

    async def failed_browser(self, pages):
        self.failure_reason = "BrowserUnavailable"
        return []

    monkeypatch.setattr("api_extractor.pipeline.ResourceCrawler", EmptyCrawler)
    monkeypatch.setattr(DynamicAnalyzer, "run", failed_browser)
    config = tmp_path / "site.json"
    config.write_text(json.dumps({"site_id": "test", "allowed_hosts": ["app.example.com"]}))
    out = tmp_path / "result.json"
    code = asyncio.run(run_pipeline("https://app.example.com/", str(config), str(out), 5))
    assert code == 1
    assert json.loads(out.read_text())["endpoints"] == []
    assert "run_status:failed" in (tmp_path / "tool.log").read_text()


def test_budget_timeout_keeps_completed_dynamic_requests(tmp_path, monkeypatch):
    async def interrupted_browser(self, pages):
        url = "https://app.example.com/api/observed"
        self.records.append({"url": url, "http_method": "GET", "method": "GET",
                             "status": 200, "resource_type": "fetch", "request_index": 0})
        self.logger.write("GET", url, 200, "dynamic", request_index=0)
        self._write_har()
        await asyncio.sleep(60)

    code, data, log = run_with_browser(tmp_path, monkeypatch, interrupted_browser)
    assert code == 0
    assert {(e["method"], e["path"]) for e in data["endpoints"]} == {
        ("GET", "/api/items"), ("GET", "/api/observed")}
    assert "run_status:incomplete_budget" in log


def test_normal_run_marks_completed(tmp_path, monkeypatch):
    async def healthy_browser(self, pages):
        return []

    code, data, log = run_with_browser(tmp_path, monkeypatch, healthy_browser)
    assert code == 0
    assert len(data["endpoints"]) == 1
    assert "run_status:completed" in log


class DummyPlaywright:
    def __init__(self, chromium):
        self.chromium = chromium

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


def make_analyzer(tmp_path):
    target = "https://app.example.com/"
    logger = JsonlLogger(tmp_path / "tool.log")
    config = SiteConfig("site", target, ["app.example.com"], [], {})
    analyzer = DynamicAnalyzer(target, config, ScopeGuard(target, config.allowed_hosts),
                               RequestGate(), logger, tmp_path)
    return analyzer, logger


def test_browser_launch_failure_is_recorded(tmp_path, monkeypatch):
    class FailingChromium:
        async def launch(self, **kwargs):
            raise OSError("simulated browser missing")

    monkeypatch.setattr("api_extractor.dynamic_analysis.async_playwright",
                        lambda: DummyPlaywright(FailingChromium()))
    analyzer, logger = make_analyzer(tmp_path)
    try:
        rows = asyncio.run(analyzer.run([]))
    finally:
        logger.close()
    assert rows == []
    assert analyzer.failure_reason == "OSError"
    assert "browser_phase_error:OSError" in (tmp_path / "tool.log").read_text()
    assert (tmp_path / "evidence/dynamic.har").is_file()


def test_all_page_navigations_failed_is_reported(tmp_path, monkeypatch):
    class FakePage:
        def on(self, *args):
            pass

        async def goto(self, *args, **kwargs):
            raise TimeoutError("simulated navigation failure")

    class FakeContext:
        async def route(self, *args):
            pass

        async def route_web_socket(self, *args):
            pass

        async def new_page(self):
            return FakePage()

        async def close(self):
            pass

    class FakeBrowser:
        async def new_context(self, **kwargs):
            return FakeContext()

        async def close(self):
            pass

    class FakeChromium:
        async def launch(self, **kwargs):
            return FakeBrowser()

    monkeypatch.setattr("api_extractor.dynamic_analysis.async_playwright",
                        lambda: DummyPlaywright(FakeChromium()))
    analyzer, logger = make_analyzer(tmp_path)
    try:
        rows = asyncio.run(analyzer.run([]))
    finally:
        logger.close()
    assert rows == []
    assert analyzer.failure_reason == "NoPagesLoaded"
    log = (tmp_path / "tool.log").read_text()
    assert "page_navigation_failed:TimeoutError" in log
    assert "browser_phase_error:NoPagesLoaded" in log
