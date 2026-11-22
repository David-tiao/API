"""S1-style localhost integration; no external traffic or browser binary required."""
import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from api_extractor.dynamic_analysis import DynamicAnalyzer
from api_extractor.pipeline import run_pipeline


class MockFrontend(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            body = b'<html><head><script src="/main.js"></script></head><body>Test</body></html>'
            typ = 'text/html'
        elif self.path == '/main.js':
            body = b'fetch("/api/users?limit=3"); fetch("/images/logo.png");'
            typ = 'application/javascript'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', typ)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def test_full_static_pipeline_on_local_site(tmp_path, monkeypatch):
    async def no_browser(self, pages):
        return []  # Playwright dynamic path requires separate Docker verification.
    monkeypatch.setattr(DynamicAnalyzer, 'run', no_browser)
    server = ThreadingHTTPServer(('127.0.0.1', 0), MockFrontend)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        url = f'http://127.0.0.1:{server.server_port}/'
        config = tmp_path / 'site.json'
        config.write_text(json.dumps({'site_id': 'local-integration',
                                     'allowed_hosts': ['127.0.0.1']}))
        result = tmp_path / 'result.json'
        exit_code = asyncio.run(run_pipeline(url, str(config), str(result), 10))
        assert exit_code == 0
        output = json.loads(result.read_text())
        assert output['site'] == 'local-integration'
        assert output['endpoints'] == []
        review = json.loads((tmp_path / 'static_candidates.json').read_text())
        assert [(x['method'], x['path']) for x in review['candidates']] == [('GET', '/api/users')]
        assert review['candidates'][0]['sources'][0]['file'].startswith('evidence/js/')
        assert (tmp_path / 'tool.log').exists()
        assert 'main.js' in (tmp_path / 'tool.log').read_text()
    finally:
        server.shutdown()
        server.server_close()
        t.join(timeout=2)
