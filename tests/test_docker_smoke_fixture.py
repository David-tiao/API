"""Fixture contract: synthetic HTML must trigger one real local JSON API fetch."""
from http.server import ThreadingHTTPServer
from pathlib import Path
import runpy
import threading
import urllib.request
import json


def test_synthetic_http_fixture_contract():
    handler = runpy.run_path(str(Path(__file__).parent / "fixtures" / "docker_smoke_site.py"))["Handler"]
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
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
