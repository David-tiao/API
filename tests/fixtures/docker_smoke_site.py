"""Synthetic HTTP fixture used exclusively by the isolated Docker smoke test.

This fixture serves no credentials and does not require Internet access.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?', 1)[0]
        if path == '/':
            status, typ, body = 200, 'text/html; charset=utf-8', (
                '<!doctype html><html><head><title>Offline API fixture</title></head>'
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
