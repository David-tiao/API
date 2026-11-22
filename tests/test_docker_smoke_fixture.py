"""Fixtures exercise SPA, SSR forms and an out-of-scope redirect entirely offline."""
from http.server import ThreadingHTTPServer
from pathlib import Path
import runpy
import threading
import urllib.error
import urllib.request
import json


def _fixture_server():
    handler = runpy.run_path(str(Path(__file__).parent / "fixtures" / "docker_smoke_site.py"))["Handler"]
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_synthetic_http_fixture_contract():
    server, thread = _fixture_server()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(base + "/", timeout=3) as r:
            html = r.read().decode()
            assert r.status == 200 and '<script src="/app.js">' in html
        with opener.open(base + "/app.js", timeout=3) as r:
            js = r.read().decode()
            assert 'fetch("/api/items")' in js
        with opener.open(base + "/api/items", timeout=3) as r:
            assert r.status == 200
            assert r.headers['Content-Type'] == 'application/json'
            assert json.loads(r.read())['items'][0]['id'] == 1
    finally:
        server.shutdown()
        thread.join(timeout=3)
        server.server_close()


def test_synthetic_ssr_form_and_api_fixture():
    server, thread = _fixture_server()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(base + "/ssr", timeout=3) as r:
            html = r.read().decode()
            assert r.status == 200
            assert '<form method="POST" action="/api/submit">' in html
            assert 'http://offscope:8765/forbidden-resource' in html
            assert '<a href="/redirect-offscope">' in html
        with opener.open(base + "/ssr-app.js", timeout=3) as r:
            assert 'fetch("/api/ssr-items")' in r.read().decode()
        with opener.open(base + "/api/ssr-items", timeout=3) as r:
            assert r.status == 200
            assert json.loads(r.read())['items'][0]['id'] == 2
    finally:
        server.shutdown()
        thread.join(timeout=3)
        server.server_close()


def test_ssr_redirect_points_outside_scope_without_following():
    server, thread = _fixture_server()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        try:
            opener.open(base + '/redirect-offscope', timeout=3)
            assert False, 'expected redirect response'
        except urllib.error.HTTPError as response:
            assert response.code == 302
            assert response.headers['Location'] == 'http://offscope:8765/forbidden-redirect'
    finally:
        server.shutdown()
        thread.join(timeout=3)
        server.server_close()


def test_long_lived_sse_fixture_emits_real_event_headers_without_waiting_for_eof():
    server, thread = _fixture_server()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(base + "/sse", timeout=3) as r:
            assert 'sse-app.js' in r.read().decode()
        with opener.open(base + "/sse-app.js", timeout=3) as r:
            assert 'new EventSource("/api/stream")' in r.read().decode()
        with opener.open(base + "/api/stream", timeout=3) as r:
            assert r.status == 200 and r.headers['Content-Type'].startswith('text/event-stream')
            assert r.readline().startswith(b'data: {"id": 3,')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_explicit_login_fixture_session_and_303_without_redirect():
    from urllib.parse import urlencode
    server, thread = _fixture_server()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(base + "/login", timeout=3) as res:
            page = res.read().decode()
            assert res.status == 200 and 'method="POST"' in page
            assert 'name="password"' in page
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        manual = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        data = urlencode({'username':'fixture-user','password':'fixture-pass'}).encode()
        req = urllib.request.Request(base+'/api/session', data=data, method='POST')
        try:
            manual.open(req, timeout=3)
            assert False, 'expected a 303 without automatic follow'
        except urllib.error.HTTPError as response:
            assert response.code == 303
            assert response.headers['Location'] == '/dashboard'
            assert 'HttpOnly' in response.headers['Set-Cookie']
        try:
            opener.open(base+'/api/private', timeout=3)
            assert False, 'requires a real session cookie'
        except urllib.error.HTTPError as response:
            assert response.code == 401
        with opener.open(urllib.request.Request(
                base+'/api/private', headers={'Cookie':'synthetic-session=ok'}), timeout=3) as response:
            assert response.status == 200
            assert json.loads(response.read())['ok'] is True
        with opener.open(urllib.request.Request(
                base+'/dashboard', headers={'Cookie':'synthetic-session=ok'}), timeout=3) as response:
            html = response.read().decode()
            assert 'src="/dashboard.js"' in html
            assert 'forbidden-auth' in html
    finally:
        server.shutdown()
        thread.join(timeout=3)
        server.server_close()
