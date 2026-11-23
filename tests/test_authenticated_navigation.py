"""Authenticated read-only route discovery; all tests are offline."""
import asyncio

from api_extractor.dynamic_analysis import DynamicAnalyzer, _safe_readonly_nav_url
from api_extractor.scope import ScopeGuard


def guard():
    return ScopeGuard("https://app.example.com/", ["app.example.com"])


def test_relative_anchor_resolution_without_fragments():
    assert _safe_readonly_nav_url(
        "https://app.example.com/dashboard", "/reports?page=2#details", guard()
    ) == "https://app.example.com/reports?page=2"
    assert _safe_readonly_nav_url(
        "https://app.example.com/ui/home", "../reports/annual", guard()
    ) == "https://app.example.com/reports/annual"


def test_external_domains_schemes_and_credentials_rejected():
    blocked = [
        "https://attacker.example.com/path",
        "//app.example.com.attacker.invalid/route",
        "mailto:test@example.com", "javascript:alert(1)", "data:text/html,example",
        "#local", "", None, 42, "https://name:secret@app.example.com/reports",
    ]
    for href in blocked:
        assert _safe_readonly_nav_url("https://app.example.com/dashboard", href, guard()) is None


def test_common_destructive_navigation_is_rejected():
    for href in [
        "/logout", "/auth/SignOut", "/users/123/delete", "/users/123/%64elete",
        "/management?action=delete", "/management?command=REVOKE",
        "/checkout/payment", "/users/3/remove", "/account/reset",
    ]:
        assert _safe_readonly_nav_url("https://app.example.com/dashboard", href, guard()) is None


class Locator:
    def __init__(self, values, fail=False):
        self.values, self.fail = values, fail

    async def evaluate_all(self, expression):
        assert "nodes.slice(0, 200)" in expression
        if self.fail:
            raise RuntimeError("Simulated DOM access failure")
        return self.values[:200]


class Page:
    url = "https://app.example.com/dashboard"

    def __init__(self, hrefs, fail=False):
        self.hrefs, self.fail = hrefs, fail

    def locator(self, selector):
        assert selector == "a[href]"
        return Locator(self.hrefs, self.fail)


def analyzer():
    instance = object.__new__(DynamicAnalyzer)
    instance.guard = guard()
    return instance


def test_collector_deduplicates_filters_and_limits_to_24():
    hrefs = ["/reports", "/reports", "/logout", "https://bad.example.com/"]
    hrefs += [f"/reports/{number}" for number in range(60)]
    result = asyncio.run(analyzer()._read_only_links(Page(hrefs)))
    assert len(result) == 24
    assert len(set(result)) == 24
    assert result[0] == "https://app.example.com/reports"
    assert all("logout" not in url and "bad." not in url for url in result)


def test_collector_handles_bad_page_without_failing_browser_stage():
    assert asyncio.run(analyzer()._read_only_links(Page([], fail=True))) == []


def test_anchor_with_query_is_kept_as_navigation_url():
    assert _safe_readonly_nav_url(
        "https://app.example.com/reports", "?year=2026#table", guard()
    ) == "https://app.example.com/reports?year=2026"
