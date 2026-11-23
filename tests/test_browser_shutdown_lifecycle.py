"""The Playwright context manager owns driver teardown; no second close command."""
import asyncio

from api_extractor.config import SiteConfig
from api_extractor.dynamic_analysis import DynamicAnalyzer
from api_extractor.jsonl_logger import JsonlLogger
from api_extractor.request_control import RequestGate
from api_extractor.scope import ScopeGuard


class FakePage:
    url = "http://fixture:8765/"

    def on(self, event, listener):
        pass

    async def goto(self, url, **kwargs):
        self.url = url
        return type("Response", (), {"status": 200})()

    async def evaluate(self, expr):
        pass


class FakeBrowser:
    def __init__(self):
        self.close_calls = 0
        self.connected = True
        self.context = FakeContext()

    async def new_context(self, **kwargs):
        return self.context

    async def close(self):
        self.close_calls += 1
        raise KeyError("simulated protocol shutdown race")

    def is_connected(self):
        return self.connected


class FakeContext:
    def __init__(self):
        self.closed = False
        self.page = FakePage()

    async def route(self, pattern, handler):
        pass

    async def route_web_socket(self, pattern, handler):
        pass

    async def new_page(self):
        return self.page

    async def close(self):
        self.closed = True


class FakeDriver:
    def __init__(self, browser, exit_fails=False):
        self.browser = browser
        self.exit_fails = exit_fails

    async def __aenter__(self):
        self.chromium = self
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.browser.connected = False
        if self.exit_fails:
            raise RuntimeError("driver shutdown failed")

    async def launch(self, **kwargs):
        return self.browser


def execute(monkeypatch, tmp_path, *, exit_fails=False):
    browser = FakeBrowser()
    driver = FakeDriver(browser, exit_fails=exit_fails)
    monkeypatch.setattr("api_extractor.dynamic_analysis.async_playwright", lambda: driver)
    cfg = SiteConfig("fixture", "http://fixture:8765/", ["fixture"], [], {})
    logger = JsonlLogger(tmp_path / "tool.log")
    analyzer = DynamicAnalyzer(cfg.entry, cfg, ScopeGuard(cfg.entry, cfg.allowed_hosts),
                               RequestGate(max_concurrency=2, max_rps=10), logger, tmp_path)

    async def no_links(page):
        return []

    async def settled(*args, **kwargs):
        return None

    monkeypatch.setattr(analyzer, "_read_only_links", no_links)
    monkeypatch.setattr(analyzer, "_settle_page", settled)
    try:
        records = asyncio.run(analyzer.run([]))
        return browser, analyzer, records, (tmp_path / "tool.log").read_text()
    finally:
        logger.close()


def test_driver_context_owns_browser_shutdown(monkeypatch, tmp_path):
    browser, analyzer, records, log = execute(monkeypatch, tmp_path)
    assert analyzer.failure_reason is None
    assert browser.context.closed is True
    assert browser.connected is False
    assert browser.close_calls == 0
    assert records == []
    assert "browser_driver_context_closed" in log
    assert "browser_phase_error" not in log


def test_real_driver_shutdown_error_remains_failure(monkeypatch, tmp_path):
    browser, analyzer, records, log = execute(monkeypatch, tmp_path, exit_fails=True)
    assert analyzer.failure_reason == "RuntimeError"
    assert "browser_phase_error:RuntimeError" in log
    assert "browser_driver_context_closed" not in log
    assert browser.close_calls == 1
