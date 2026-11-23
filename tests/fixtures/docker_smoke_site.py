"""Synthetic SPA + SSR form fixture used only in isolated Docker quality checks.

All endpoints and the out-of-scope host are synthetic; no external network needed.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import time
from urllib.parse import parse_qs


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?', 1)[0]
        if path == '/':
            status, typ, body = 200, 'text/html; charset=utf-8', (
                '<!doctype html><html><head><title>Offline SPA fixture</title></head>'
                '<body><h1>Offline Fixture</h1><script src="/app.js"></script></body></html>'
            ).encode()
        elif path == '/app.js':
            status, typ, body = 200, 'application/javascript; charset=utf-8', (
                'window.fixtureReady=false;'
                'fetch("/api/items").then(r=>r.json()).then(data=>{'
                'window.fixtureItems=data.items; window.fixtureReady=true;});'
            ).encode()
        elif path == '/api/items':
            status, typ, body = 200, 'application/json', json.dumps({
                'items': [{'id': 1, 'name': 'synthetic-only'}], 'source': 'offline'
            }).encode()
        elif path == '/spa-hash':
            # The API is not requested until the SPA navigates to a real hash
            # route. Collecting JS hints alone must not pass HAR verification.
            status, typ, body = 200, 'text/html; charset=utf-8', (
                '<!doctype html><html><body><h1>Hash router exercise</h1>'
                '<a href="#/reports">Reports route</a>'
                '<a href="#/logout">Unsafe logout route</a>'
                '<a href="#/manage?action=delete">Unsafe action route</a>'
                '<script>'
                'function onRoute() {'
                '  if (location.hash === "#/reports") {'
                '    fetch("/api/hash-report").then(r=>r.json()).then(data=>{'
                '      window.hashReport=data.source;'
                '    });'
                '  }'
                '}'
                'addEventListener("hashchange", onRoute);'
                'onRoute();'
                '</script></body></html>'
            ).encode()
        elif path == '/api/hash-report':
            status, typ, body = 200, 'application/json', (
                '{"source":"synthetic-hash-navigation","observed":true}'
            ).encode()
        elif path == '/ssr':
            # The form is intentionally NOT submitted: unknown POST operations
            # must remain static hints, not synthetic dynamic request evidence.
            status, typ, body = 200, 'text/html; charset=utf-8', (
                '<!doctype html><html><head><title>Offline SSR fixture</title></head>'
                '<body><h1>SSR exercise</h1>'
                '<form method="POST" action="/api/submit">'
                '<input name="item" required><button type="submit">Save</button></form>'
                '<a href="/redirect-offscope">Redirect trap</a>'
                '<img src="http://offscope:8765/forbidden-resource" alt="blocked">'
                '<script src="/ssr-app.js"></script>'
                '</body></html>'
            ).encode()
        elif path == '/ssr-app.js':
            status, typ, body = 200, 'application/javascript; charset=utf-8', (
                'fetch("/api/ssr-items").then(r=>r.json()).then('
                'data=>{window.ssrItems=data.items;});'
            ).encode()
        elif path == '/api/ssr-items':
            status, typ, body = 200, 'application/json', json.dumps({
                'items': [{'id': 2, 'name': 'ssr-synthetic'}], 'source': 'offline-ssr'
            }).encode()
        elif path == '/sse':
            status, typ, body = 200, 'text/html; charset=utf-8', (
                '<!doctype html><html><head><title>Offline SSE fixture</title></head>'
                '<body><h1>Server event exercise</h1><script src="/sse-app.js"></script></body></html>'
            ).encode()
        elif path == '/sse-app.js':
            status, typ, body = 200, 'application/javascript; charset=utf-8', (
                'window.streamSample=null;'
                'const stream=new EventSource("/api/stream");'
                'stream.onmessage=(ev)=>{window.streamSample=JSON.parse(ev.data);stream.close();};'
            ).encode()
        elif path == '/api/stream':
            # A genuine, deliberately long-lived stream; Route.fetch() cannot
            # collect the entire body. V17 must sample an authentic first event.
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(b'data: {"id": 3, "kind": "synthetic-sse"}\n\n')
            self.wfile.flush()
            time.sleep(20)
            return
        elif path == '/login':
            status, typ, body = 200, 'text/html; charset=utf-8', (
                '<!doctype html><html><head><title>Synthetic login</title></head>'
                '<body><h1>Login</h1><form action="/api/session" method="POST">'
                '<input name="username" autocomplete="username">'
                '<input type="password" name="password">'
                '<button type="submit">Sign in</button></form></body></html>'
            ).encode()
        elif path == '/dashboard':
            cookie = self.headers.get('Cookie', '')
            if 'synthetic-session=ok' not in cookie:
                status, typ, body = 401, 'text/html; charset=utf-8', b'Unauthorized'
            else:
                status, typ, body = 200, 'text/html; charset=utf-8', (
                    '<!doctype html><html><head><title>Private dashboard</title></head>'
                    '<body><h1>Dashboard</h1><a href="/reports">Reports</a>'
                    '<img src="http://offscope:8765/forbidden-auth" alt="blocked">'
                    '<script src="/dashboard.js"></script></body></html>'
                ).encode()
        elif path == '/dashboard.js':
            status, typ, body = 200, 'application/javascript', (
                'fetch("/api/private").then(r=>r.json()).then(data=>'
                '{window.privateFixture=data.ok;});'
            ).encode()
        elif path == '/api/private':
            cookie = self.headers.get('Cookie', '')
            if 'synthetic-session=ok' not in cookie:
                status, typ, body = 401, 'application/json', b'{"error":"unauthorized"}'
            else:
                status, typ, body = 200, 'application/json', b'{"ok":true,"subject":"fixture-user"}'
        elif path == '/reports':
            cookie = self.headers.get('Cookie', '')
            if 'synthetic-session=ok' not in cookie:
                status, typ, body = 401, 'text/html; charset=utf-8', b'Unauthorized'
            else:
                status, typ, body = 200, 'text/html; charset=utf-8', (
                    '<!doctype html><html><body><h1>Reports</h1>'
                    '<a href="/reports/annual">Annual report</a>'
                    '<a href="/logout">Do not visit logout</a></body></html>'
                ).encode()
        elif path == '/reports/annual':
            cookie = self.headers.get('Cookie', '')
            if 'synthetic-session=ok' not in cookie:
                status, typ, body = 401, 'text/html; charset=utf-8', b'Unauthorized'
            else:
                status, typ, body = 200, 'text/html; charset=utf-8', (
                    '<!doctype html><html><body><h1>Annual report</h1>'
                    '<script src="/report-app.js"></script></body></html>'
                ).encode()
        elif path == '/report-app.js':
            status, typ, body = 200, 'application/javascript', (
                'fetch("/api/annual-report").then(r=>r.json()).then(data=>'
                '{window.annualFixture=data.year;});'
            ).encode()
        elif path == '/api/annual-report':
            cookie = self.headers.get('Cookie', '')
            if 'synthetic-session=ok' not in cookie:
                status, typ, body = 401, 'application/json', b'{"error":"unauthorized"}'
            else:
                status, typ, body = 200, 'application/json', b'{"year":2026,"value":"synthetic-annual"}'
        elif path == '/redirect-offscope':
            # The crawler and browser must refuse the second-hop destination.
            self.send_response(302)
            self.send_header('Location', 'http://offscope:8765/forbidden-redirect')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        else:
            status, typ, body = 404, 'text/plain', b'Not found'
        self.send_response(status)
        self.send_header('Content-Type', typ)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        path = self.path.split('?', 1)[0]
        # Only the explicitly configured login flow may submit a POST.
        if path != '/api/session':
            self.send_response(405)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        length = min(int(self.headers.get('Content-Length', '0')), 8192)
        body = self.rfile.read(length).decode('utf-8', errors='replace')
        fields = parse_qs(body)
        if fields.get('username') != ['fixture-user'] or fields.get('password') != ['fixture-pass']:
            self.send_response(403)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        self.send_response(303)
        self.send_header('Location', '/dashboard')
        self.send_header('Set-Cookie', 'synthetic-session=ok; HttpOnly; Path=/; SameSite=Lax')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def log_message(self, format, *args):
        print('fixture: ' + (format % args), flush=True)


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 8765), Handler).serve_forever()
