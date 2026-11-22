"""V18: route.fetch POST -> GET redirects are explicit and preserve R5/R6."""
import asyncio
import json
from types import SimpleNamespace

from api_extractor.config import SiteConfig
from api_extractor.dynamic_analysis import DynamicAnalyzer
from api_extractor.jsonl_logger import JsonlLogger
from api_extractor.request_control import RequestGate
from api_extractor.scope import ScopeGuard


class Reply:
    def __init__(self, status, location=None):
        self.status = status
        self.headers = {'location': location} if location else {'content-type': 'text/html'}


class Route:
    def __init__(self, url, responses, method='POST'):
        self.request = SimpleNamespace(
            url=url, method=method,
            headers={'Accept':'text/html','User-Agent':'SyntheticBrowser/1',
                     'Content-Type':'application/x-www-form-urlencoded',
                     'Content-Length':'37','Cookie':'secret-cookie',
                     'Authorization':'Bearer fake-secret'})
        self.responses = responses
        self.fetches = []
        self.aborted = False
        self.fulfilled = False

    async def fetch(self, **kwargs):
        assert kwargs.get('max_redirects') == 0
        self.fetches.append(kwargs)
        return self.responses[len(self.fetches)-1]

    async def abort(self, reason=None):
        self.aborted = True

    async def fulfill(self, **kwargs):
        self.fulfilled = True


def execute(tmp_path, route):
    target = 'http://fixture:8765/'
    cfg = SiteConfig('local', target, ['fixture'], [], {})
    logger = JsonlLogger(tmp_path/'tool.log')
    analyzer = DynamicAnalyzer(target, cfg, ScopeGuard(target, cfg.allowed_hosts),
                               RequestGate(max_rps=1000, max_concurrency=1), logger, tmp_path)
    try:
        asyncio.run(analyzer._route_http(route))
        return analyzer, (tmp_path/'tool.log').read_text()
    finally:
        analyzer._limiter.close()
        logger.close()


def test_same_host_303_login_issues_get_without_post_body_or_secrets(tmp_path):
    route = Route('http://fixture:8765/api/session', [Reply(303, '/dashboard'), Reply(200)])
    analyzer, log = execute(tmp_path, route)
    assert route.fulfilled and not route.aborted and len(route.fetches)==2
    opts = route.fetches[1]
    assert opts['url'] == 'http://fixture:8765/dashboard'
    assert opts['method'] == 'GET'
    assert opts['post_data'] == ''
    lower_headers = {k.lower():v for k,v in opts['headers'].items()}
    assert set(lower_headers) <= {'accept','user-agent','accept-language'}
    assert lower_headers['accept'] == 'text/html'
    assert analyzer._first_wire_status[id(route.request)] == 303
    rows = [json.loads(s) for s in log.splitlines()]
    assert [(x['method'],x['status']) for x in rows if x['phase']=='redirect'] == [('POST',303),('GET',200)]
    assert 'secret-cookie' not in log and 'fake-secret' not in log


def test_302_post_login_also_switches_get(tmp_path):
    route=Route('http://fixture:8765/api/session', [Reply(302,'/dashboard'),Reply(200)])
    _,_ = execute(tmp_path,route)
    assert route.fulfilled and route.fetches[1]['method']=='GET'


def test_offscope_303_after_login_never_makes_second_request(tmp_path):
    route=Route('http://fixture:8765/api/session',[Reply(303,'http://offscope:8765/dashboard')])
    _,log=execute(tmp_path,route)
    assert route.aborted and not route.fulfilled and len(route.fetches)==1
    assert 'browser_redirect_blocked_by_scope' in log


def test_post_307_cannot_repeat_mutation(tmp_path):
    route=Route('http://fixture:8765/api/session',[Reply(307,'/dashboard')])
    _,log=execute(tmp_path,route)
    assert route.aborted and len(route.fetches)==1
    assert 'browser_redirect_unsafe_transition' in log


def test_get_http_to_https_same_host_upgrade(tmp_path):
    route=Route('http://fixture:8765/public',[Reply(302,'https://fixture:8765/public'),Reply(200)],method='GET')
    _,log=execute(tmp_path,route)
    assert route.fulfilled and not route.aborted
    follow=route.fetches[1]
    assert follow['url']=='https://fixture:8765/public'
    assert follow['method']=='GET'
    assert 'Authorization' not in follow['headers'] and 'Cookie' not in follow['headers']
    assert 'browser_redirect_unsafe_transition' not in log


def test_https_to_http_downgrade_is_denied(tmp_path):
    route=Route('https://fixture:8765/public',[Reply(302,'http://fixture:8765/public')],method='GET')
    _,log=execute(tmp_path,route)
    assert route.aborted and len(route.fetches)==1
    assert 'browser_redirect_unsafe_transition' in log


def test_login_redirect_to_another_port_is_denied(tmp_path):
    route=Route('http://fixture:8765/api/session',[Reply(303,'http://fixture:9000/dashboard')])
    _,log=execute(tmp_path,route)
    assert route.aborted and len(route.fetches)==1
    assert 'browser_redirect_unsafe_transition' in log


def test_successful_plain_post_still_fulfilled(tmp_path):
    route=Route('http://fixture:8765/api/session',[Reply(204)])
    _,log=execute(tmp_path,route)
    assert route.fulfilled and len(route.fetches)==1 and 'route_fetch_redirect' not in log
