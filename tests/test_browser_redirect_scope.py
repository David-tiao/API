"""Regression: Playwright redirected hops must be checked before connection."""
import asyncio
from types import SimpleNamespace

from api_extractor.config import SiteConfig
from api_extractor.dynamic_analysis import DynamicAnalyzer
from api_extractor.jsonl_logger import JsonlLogger
from api_extractor.request_control import RequestGate
from api_extractor.scope import ScopeGuard


class MockResponse:
    def __init__(self, status, location=None):
        self.status = status
        self.headers = {"location": location} if location else {}


class MockRoute:
    def __init__(self, url, responses, method="GET"):
        self.request = SimpleNamespace(
            url=url, method=method,
            headers={"Accept": "text/html", "User-Agent": "FixtureBrowser/1",
                     "Content-Type": "application/x-www-form-urlencoded",
                     "Cookie": "secret-cookie"}
        )
        self.responses = responses
        self.fetches = []
        self.aborted = False
        self.fulfilled = False

    async def fetch(self, **kwargs):
        self.fetches.append(kwargs)
        assert kwargs.get("max_redirects") == 0, "Automatic redirects must be disabled"
        return self.responses[len(self.fetches) - 1]

    async def fulfill(self, **kwargs):
        self.fulfilled = True

    async def abort(self, reason=None):
        self.aborted = True


def execute(tmp_path, route):
    target = "http://fixture:8765/"
    cfg = SiteConfig("test", target, ["fixture"], [], {})
    logger = JsonlLogger(tmp_path / "tool.log")
    gate = RequestGate(max_rps=1000, max_concurrency=1)
    analyzer = DynamicAnalyzer(target, cfg, ScopeGuard(target, cfg.allowed_hosts),
                               gate, logger, tmp_path)
    try:
        asyncio.run(analyzer._route_http(route))
        analyzer._limiter.close()
        return (tmp_path / "tool.log").read_text()
    finally:
        logger.close()


def test_offscope_redirect_never_reaches_second_hop(tmp_path):
    route = MockRoute("http://fixture:8765/redirect",
                      [MockResponse(302, "http://offscope:8765/forbidden-redirect")])
    log = execute(tmp_path, route)
    assert route.aborted and not route.fulfilled and len(route.fetches) == 1
    assert "browser_redirect_blocked_by_scope" in log


def test_allowed_relative_redirect_is_explicitly_followed(tmp_path):
    route = MockRoute("http://fixture:8765/start", [
        MockResponse(302, "/api/items"), MockResponse(200)
    ])
    execute(tmp_path, route)
    assert route.fulfilled and not route.aborted
    assert len(route.fetches) == 2
    assert route.fetches[1]["url"] == "http://fixture:8765/api/items"


def test_initial_external_host_is_blocked_before_fetch(tmp_path):
    route = MockRoute("http://offscope:8765/forbidden-resource", [MockResponse(200)])
    execute(tmp_path, route)
    assert route.aborted and route.fetches == []


def test_post_302_same_host_switches_to_get_without_replaying_body(tmp_path):
    route = MockRoute("http://fixture:8765/api/login", [
        MockResponse(302, "/dashboard"), MockResponse(200)
    ], method="POST")
    log = execute(tmp_path, route)
    assert route.fulfilled and not route.aborted and len(route.fetches) == 2
    hop = route.fetches[1]
    assert hop["url"] == "http://fixture:8765/dashboard"
    assert hop["method"] == "GET" and hop["post_data"] == ""
    assert "Cookie" not in hop["headers"] and "Content-Type" not in hop["headers"]
    assert "Authorization" not in hop["headers"]
    assert "browser_redirect_unsafe_transition" not in log


def test_authorized_get_http_to_https_upgrade_is_explicit(tmp_path):
    route = MockRoute("http://fixture:8765/start", [
        MockResponse(302, "https://fixture:8765/start"), MockResponse(200)
    ])
    log = execute(tmp_path, route)
    assert route.fulfilled and not route.aborted and len(route.fetches) == 2
    hop = route.fetches[1]
    assert hop["url"] == "https://fixture:8765/start"
    assert hop["method"] == "GET"
    assert "Cookie" not in hop["headers"] and "Content-Type" not in hop["headers"]
    assert "browser_redirect_unsafe_transition" not in log


def test_redirect_loop_stops_after_seven_hops(tmp_path):
    route = MockRoute("http://fixture:8765/start", [
        MockResponse(302, "/start") for _ in range(7)
    ])
    log = execute(tmp_path, route)
    assert route.aborted and len(route.fetches) == 7
    assert "browser_redirect_limit" in log


def test_normal_response_is_fulfilled(tmp_path):
    route = MockRoute("http://fixture:8765/api/items", [MockResponse(200)])
    execute(tmp_path, route)
    assert route.fulfilled and not route.aborted and len(route.fetches) == 1
