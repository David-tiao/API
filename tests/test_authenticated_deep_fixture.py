"""Offline synthetic S3 fixture verifies that the report API is not public."""
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
import runpy
import threading
import urllib.error
import urllib.request


def test_authenticated_two_hop_fixture():
    handler = runpy.run_path(
        str(Path(__file__).parent / "fixtures" / "docker_smoke_site.py")
    )["Handler"]
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        for path in ("/reports", "/reports/annual", "/api/annual-report"):
            try:
                opener.open(base + path, timeout=3)
                assert False, f"{path} must require a cookie"
            except urllib.error.HTTPError as exc:
                assert exc.code == 401

        def get(path):
            request = urllib.request.Request(
                base + path, headers={"Cookie": "synthetic-session=ok"}
            )
            with opener.open(request, timeout=3) as response:
                assert response.status == 200
                return response.read().decode("utf-8")

        assert '<a href="/reports/annual">' in get("/reports")
        assert '<script src="/report-app.js">' in get("/reports/annual")
        assert 'fetch("/api/annual-report")' in get("/report-app.js")
        assert json.loads(get("/api/annual-report"))["year"] == 2026
    finally:
        server.shutdown()
        worker.join(timeout=3)
        server.server_close()
