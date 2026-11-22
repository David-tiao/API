"""WS routing tests use fake routes, not live network connections."""
import asyncio
from api_extractor.config import SiteConfig
from api_extractor.dynamic_analysis import DynamicAnalyzer
from api_extractor.jsonl_logger import JsonlLogger
from api_extractor.request_control import RequestGate
from api_extractor.scope import ScopeGuard


class FakeRoute:
    def __init__(self, url, error=False):
        self.url, self.error = url, error
        self.events = []
        self.closed = False
        self.server = None

    async def close(self):
        self.closed = True

    def on_close(self, callback):
        self.events.append(callback)

    def connect_to_server(self):
        if self.error:
            raise RuntimeError("mock connect failure")
        self.server = FakeRoute(self.url)
        return self.server

    def emit_close(self):
        for callback in self.events:
            callback(1000, 'closed')


def analyzer(tmp_path, max_concurrency=8, max_rps=1000):
    target = 'https://app.example.com/'
    cfg = SiteConfig('test', target, ['app.example.com'], [], {})
    log = JsonlLogger(tmp_path / 'tool.log')
    a = DynamicAnalyzer(target, cfg, ScopeGuard(target, cfg.allowed_hosts),
                        RequestGate(max_concurrency=max_concurrency, max_rps=max_rps),
                        log, tmp_path)
    return a, log


def test_ws_slot_is_held_until_close(tmp_path):
    a, log = analyzer(tmp_path)
    try:
        route = FakeRoute('wss://app.example.com/feed')
        asyncio.run(a._route_websocket(route))
        assert len(a._limiter.active) == 1
        route.emit_close()
        assert len(a._limiter.active) == 0
    finally:
        a._limiter.close()
        log.close()


def test_server_close_releases_slot(tmp_path):
    a, log = analyzer(tmp_path)
    try:
        route = FakeRoute('wss://app.example.com/feed')
        asyncio.run(a._route_websocket(route))
        route.server.emit_close()
        assert not a._limiter.active
    finally:
        a._limiter.close()
        log.close()


def test_out_of_scope_ws_is_closed_without_slot(tmp_path):
    a, log = analyzer(tmp_path)
    try:
        route = FakeRoute('wss://unrelated.example.com/feed')
        asyncio.run(a._route_websocket(route))
        assert route.closed and not a._limiter.active
    finally:
        a._limiter.close()
        log.close()


def test_connect_failure_does_not_leak_slot(tmp_path):
    a, log = analyzer(tmp_path)
    try:
        route = FakeRoute('wss://app.example.com/feed', error=True)
        try:
            asyncio.run(a._route_websocket(route))
            raise AssertionError('expected failure')
        except RuntimeError as exc:
            assert 'mock' in str(exc)
        assert not a._limiter.active
    finally:
        a._limiter.close()
        log.close()


def test_two_ws_cannot_exceed_one_concurrent_slot(tmp_path):
    a, log = analyzer(tmp_path, max_concurrency=1)
    async def scenario():
        first = FakeRoute('wss://app.example.com/one')
        second = FakeRoute('wss://app.example.com/two')
        await a._route_websocket(first)
        waiter = asyncio.create_task(a._route_websocket(second))
        await asyncio.sleep(0.02)
        assert not waiter.done() and len(a._limiter.active) == 1
        first.emit_close()
        await asyncio.wait_for(waiter, 0.5)
        assert len(a._limiter.active) == 1
        second.server.emit_close()
        assert not a._limiter.active
    try:
        asyncio.run(scenario())
    finally:
        a._limiter.close()
        log.close()


def test_websocket_uses_shared_rate_limiter(tmp_path):
    import time
    a, log = analyzer(tmp_path, max_rps=20)
    async def scenario():
        first = FakeRoute('wss://app.example.com/first')
        second = FakeRoute('wss://app.example.com/second')
        await a._route_websocket(first)
        started = time.monotonic()
        first.emit_close()
        await a._route_websocket(second)
        elapsed = time.monotonic() - started
        assert elapsed >= 0.04
        second.emit_close()
    try:
        asyncio.run(scenario())
    finally:
        a._limiter.close()
        log.close()
