"""SSE route adapter: real upstream only, never auto-redirect or forge events."""
import asyncio
from types import SimpleNamespace

import httpx

from api_extractor.config import SiteConfig
from api_extractor.dynamic_analysis import DynamicAnalyzer
from api_extractor.jsonl_logger import JsonlLogger
from api_extractor.request_control import RequestGate
from api_extractor.scope import ScopeGuard


class Route:
    def __init__(self, url='http://fixture:8765/api/stream', method='GET'):
        self.request = SimpleNamespace(url=url, method=method, resource_type='eventsource')
        self.aborted = False
        self.fulfilled = None

    async def abort(self, reason=None):
        self.aborted = True

    async def fulfill(self, **kwargs):
        assert type(kwargs.get('body')) is bytes, 'Playwright requires bytes, not bytearray'
        self.fulfilled = kwargs


def analyzer(tmp_path, handler):
    target = 'http://fixture:8765/'
    config = SiteConfig('test', target, ['fixture'], [], {})
    logger = JsonlLogger(tmp_path / 'tool.log')
    gate = RequestGate(max_concurrency=1, max_rps=1000)
    a = DynamicAnalyzer(target, config, ScopeGuard(target, config.allowed_hosts), gate,
                        logger, tmp_path, sse_transport=httpx.MockTransport(handler))
    return a, logger, gate


def test_sse_fulfills_only_actual_event_bytes(tmp_path):
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(200, headers={'content-type':'text/event-stream'},
                              content=b'data: {"observed": true}\n\n')
    a, logger, gate = analyzer(tmp_path, handle)
    route = Route()
    try:
        asyncio.run(a._route_http(route))
        assert route.fulfilled is not None and not route.aborted
        assert route.fulfilled['body'] == b'data: {"observed": true}\n\n'
        assert route.fulfilled['status'] == 200
        assert len(calls) == 1 and calls[0].method == 'GET'
        assert 'authorization' not in calls[0].headers
        assert gate._semaphore._value == 1
    finally:
        logger.close()


def test_out_of_scope_sse_never_opens_upstream(tmp_path):
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(200, headers={'content-type':'text/event-stream'},
                              content=b'data: should never occur\n\n')
    a, logger, gate = analyzer(tmp_path, handle)
    route = Route('http://offscope:8765/forbidden-resource')
    try:
        asyncio.run(a._route_http(route))
        assert route.aborted and route.fulfilled is None and calls == []
        assert gate._semaphore._value == 1
    finally:
        logger.close()


def test_upstream_redirect_does_not_follow_or_fulfill(tmp_path):
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(302, headers={
            'location':'http://offscope:8765/forbidden-redirect',
            'content-type':'text/event-stream'})
    a, logger, gate = analyzer(tmp_path, handle)
    route = Route()
    try:
        asyncio.run(a._route_http(route))
        assert route.aborted and route.fulfilled is None
        assert len(calls) == 1
        assert gate._semaphore._value == 1
    finally:
        logger.close()


def test_non_get_eventsource_aborts_safely(tmp_path):
    calls=[]
    def handle(request):
        calls.append(request)
        return httpx.Response(200, headers={'content-type':'text/event-stream'},
                              content=b'data: not allowed\n\n')
    a, logger, _=analyzer(tmp_path,handle)
    try:
        route=Route(method='POST')
        asyncio.run(a._route_http(route))
        assert route.aborted and calls == []
    finally:
        logger.close()


def test_sse_reconnect_attempts_are_bounded(tmp_path):
    calls=[]
    def handle(request):
        calls.append(request)
        return httpx.Response(200, headers={'content-type':'text/event-stream'},
                              content=b'data: first only\n\n')
    a, logger, gate=analyzer(tmp_path,handle)
    async def scenario():
        rows=[Route() for _ in range(4)]
        for row in rows:
            await a._route_http(row)
        return rows
    try:
        rows=asyncio.run(scenario())
        assert len(calls) == 3
        assert all(x.fulfilled for x in rows[:3])
        assert rows[3].aborted and rows[3].fulfilled is None
        assert gate._semaphore._value == 1
    finally:
        logger.close()


def test_invalid_body_not_promoted_to_observed_sse(tmp_path):
    def handle(request):
        return httpx.Response(200,headers={'content-type':'text/event-stream'},
                              content=b':keepalive\n\n')
    a, logger, gate=analyzer(tmp_path,handle)
    route=Route()
    try:
        asyncio.run(a._route_http(route))
        assert route.aborted and route.fulfilled is None
        assert gate._semaphore._value == 1
    finally:
        logger.close()
