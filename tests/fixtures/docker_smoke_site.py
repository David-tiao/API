"""Synthetic SPA + SSR form fixture used only in isolated Docker quality checks.

All endpoints and the out-of-scope host are synthetic; no external network needed.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json


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

    def log_message(self, format, *args):
        print('fixture: ' + (format % args), flush=True)


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 8765), Handler).serve_forever()
