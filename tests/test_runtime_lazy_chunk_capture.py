"""Late-loaded JavaScript should produce bounded offline AST hints, never wire proof."""
from __future__ import annotations

import asyncio
from pathlib import Path

from api_extractor.dynamic_analysis import DynamicAnalyzer
from api_extractor.scope import ScopeGuard
from api_extractor.static_analysis import StaticAnalyzer


class FakeRequest:
    def __init__(self, kind="script"):
        self.resource_type = kind


class FakeResponse:
    def __init__(self, url, body=b'function report(){return fetch("/api/lazy")}', *,
                 kind="script", status=200, headers=None):
        self.request = FakeRequest(kind)
        self.url = url
        self.status = status
        self.data = body
        self.headers = headers or {"content-type": "application/javascript"}
        self.body_calls = 0

    async def all_headers(self):
        return self.headers

    async def body(self):
        self.body_calls += 1
        return self.data


def analyzer(tmp_path):
    instance = object.__new__(DynamicAnalyzer)
    instance.guard = ScopeGuard("https://app.example.test/", ["app.example.test"])
    instance.out_dir = tmp_path
    instance.script_records = []
    instance._script_urls = set()
    instance._script_bytes = 0
    return instance


def test_runtime_script_stored_and_detected_without_network_replay(tmp_path):
    a = analyzer(tmp_path)
    response = FakeResponse("https://app.example.test/chunks/reports.js")
    asyncio.run(a._capture_runtime_script(response))
    assert response.body_calls == 1
    assert len(a.script_records) == 1
    file = tmp_path / a.script_records[0].local_file
    assert file.is_file()
    assert file.read_bytes() == response.data
    static = StaticAnalyzer(tmp_path, tmp_path, a.guard)
    rows, _ = static._regex_fallback(a.script_records[0])
    assert [(x["method"], x["url"], x["source"]) for x in rows] == [
        ("GET", "https://app.example.test/api/lazy", "regex")
    ]
    assert rows[0]["file"] == a.script_records[0].local_file


def test_runtime_script_never_captures_offscope_or_non_script(tmp_path):
    a = analyzer(tmp_path)
    for url, kind in [
        ("https://evil.example.org/evil.js", "script"),
        ("https://app.example.test/graph.json", "fetch"),
    ]:
        response = FakeResponse(url, kind=kind)
        asyncio.run(a._capture_runtime_script(response))
        assert response.body_calls == 0
    assert a.script_records == []
    assert not (tmp_path / "evidence").exists()


def test_wrong_mime_and_non_js_path_are_excluded(tmp_path):
    a = analyzer(tmp_path)
    response = FakeResponse("https://app.example.test/assets/logo.png",
                            headers={"content-type": "image/png"})
    asyncio.run(a._capture_runtime_script(response))
    assert response.body_calls == 0
    assert a.script_records == []


def test_declared_oversize_script_is_not_downloaded(tmp_path):
    a = analyzer(tmp_path)
    response = FakeResponse("https://app.example.test/huge.js",
                            headers={"content-type": "application/javascript",
                                     "content-length": str(2 * 1024 * 1024 + 1)})
    asyncio.run(a._capture_runtime_script(response))
    assert response.body_calls == 0
    assert not a.script_records


def test_untrusted_content_length_and_bad_status_fail_closed(tmp_path):
    a = analyzer(tmp_path)
    bad = FakeResponse("https://app.example.test/x.js",
                       headers={"content-type": "text/javascript",
                                "content-length": "not-a-number"})
    denied = FakeResponse("https://app.example.test/404.js", status=404)
    asyncio.run(a._capture_runtime_script(bad))
    asyncio.run(a._capture_runtime_script(denied))
    assert a.script_records == []
    assert bad.body_calls == 0 and denied.body_calls == 0


def test_script_dedup_and_per_file_size_ceiling(tmp_path):
    a = analyzer(tmp_path)
    u = "https://app.example.test/unique.js"
    r1 = FakeResponse(u, b'fetch("/api/one")')
    r2 = FakeResponse(u, b'fetch("/api/two")')
    big = FakeResponse("https://app.example.test/too-big.js", b"x" * (2 * 1024 * 1024 + 1))
    for r in (r1, r2, big):
        asyncio.run(a._capture_runtime_script(r))
    assert len(a.script_records) == 1
    assert a.script_records[0].url == u
    assert a._script_bytes == len(r1.data)
    assert r2.body_calls == 0


def test_total_byte_and_count_caps(tmp_path):
    a = analyzer(tmp_path)
    a._script_bytes = 8 * 1024 * 1024
    blocked = FakeResponse("https://app.example.test/z.js")
    asyncio.run(a._capture_runtime_script(blocked))
    assert blocked.body_calls == 0
    a._script_bytes = 0
    a.script_records = [None] * 32
    blocked2 = FakeResponse("https://app.example.test/y.js")
    asyncio.run(a._capture_runtime_script(blocked2))
    assert blocked2.body_calls == 0


def test_script_source_outside_current_output_root_not_created(tmp_path):
    a = analyzer(tmp_path)
    source = FakeResponse("https://app.example.test/valid.js", b'console.log("example")')
    asyncio.run(a._capture_runtime_script(source))
    assert all(Path(x.local_file).parts[0] == "evidence" for x in a.script_records)
    assert len(list(tmp_path.rglob("*"))) <= 3
