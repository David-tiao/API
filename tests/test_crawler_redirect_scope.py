"""R5 redirects: only a prevalidated host is ever passed to HTTPX transport."""
import asyncio
import json

import httpx

from api_extractor.config import SiteConfig
from api_extractor.crawler import ResourceCrawler
from api_extractor.jsonl_logger import JsonlLogger
from api_extractor.request_control import RequestGate
from api_extractor.scope import ScopeGuard


BASE = "http://fixture:8765/"


def exercise(tmp_path, transport_handler):
    config = SiteConfig("scope-fixture", BASE, ["fixture"], [], {})
    logger = JsonlLogger(tmp_path / "tool.log")

    async def run():
        async with ResourceCrawler(
            BASE, config, ScopeGuard(BASE, config.allowed_hosts),
            RequestGate(max_rps=1000), logger, tmp_path,
        ) as crawler:
            # The actual client defaults to no redirects. Replace only its
            # transport so a forbidden host would be observable, not contacted.
            await crawler._client.aclose()
            crawler._client = httpx.AsyncClient(
                transport=httpx.MockTransport(transport_handler),
                follow_redirects=False,
            )
            return await crawler._get(BASE + "start")

    try:
        return asyncio.run(run())
    finally:
        logger.close()


def test_cross_host_redirect_is_blocked_before_outbound_request(tmp_path):
    requested = []

    def handle(request):
        requested.append(str(request.url))
        if request.url.path == "/start":
            return httpx.Response(302, headers={"Location": "http://offscope:8765/forbidden-redirect"})
        raise AssertionError("Forbidden HTTP request was actually sent")

    assert exercise(tmp_path, handle) is None
    assert requested == [BASE + "start"]
    log = [json.loads(x) for x in (tmp_path / "tool.log").read_text().splitlines()]
    assert any(row.get("note") == "redirect_blocked_by_scope" for row in log)


def test_relative_in_scope_redirect_is_followed_with_new_gate_slot(tmp_path):
    requested = []

    def handle(request):
        requested.append(str(request.url))
        if request.url.path == "/start":
            return httpx.Response(302, headers={"Location": "/api/items"})
        return httpx.Response(200, headers={"Content-Type": "application/json"}, json={"ok": True})

    got = exercise(tmp_path, handle)
    assert got is not None
    assert got[0] == BASE + "api/items" and got[2] == 200
    assert requested == [BASE + "start", BASE + "api/items"]


def test_redirect_url_userinfo_is_blocked_without_leaking_password(tmp_path):
    attempted = []

    def handle(request):
        attempted.append(str(request.url))
        return httpx.Response(302, headers={
            "Location": "http://alice:topsecret@fixture:8765/private",
        })

    assert exercise(tmp_path, handle) is None
    assert attempted == [BASE + "start"]
    assert "topsecret" not in (tmp_path / "tool.log").read_text()


def test_bounded_redirect_loop(tmp_path):
    attempted = []

    def handle(request):
        attempted.append(str(request.url))
        return httpx.Response(302, headers={"Location": "/start"})

    assert exercise(tmp_path, handle) is None
    assert len(attempted) == 6
    assert "redirect_limit" in (tmp_path / "tool.log").read_text()
