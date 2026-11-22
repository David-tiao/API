"""V14: measure actual extractor outputs from two independent offline runs."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import httpx

from api_extractor.crawler import ScriptRecord
from api_extractor.dynamic_analysis import DynamicAnalyzer
from api_extractor.offline_benchmark import evaluate_pair, evaluate_run, load_truth
from api_extractor.pipeline import run_pipeline
from api_extractor.verification import ExplicitGetVerifier


class LocalFixtureCrawler:
    def __init__(self, target, config, guard, gate, logger, out_dir):
        self.out_dir, self.target = Path(out_dir), target

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def crawl(self):
        script = self.out_dir / "evidence/js/local.js"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text('fetch("/api/items")', encoding="utf-8")
        return SimpleNamespace(scripts=[ScriptRecord(self.target + "local.js", script.read_text(),
                                                     "evidence/js/local.js")],
                               pages=[], links=[], forms=[])


def test_two_independent_pipeline_runs_have_real_correlated_mock_evidence(tmp_path, monkeypatch):
    """No live site; exact GET is explicitly allowed and MockTransport records it."""
    sent = []
    def handler(request):
        sent.append((request.method, str(request.url)))
        return httpx.Response(200, json={"items": [1]})

    monkeypatch.setattr("api_extractor.pipeline.ResourceCrawler", LocalFixtureCrawler)

    async def no_browser(self, pages):
        return []
    monkeypatch.setattr(DynamicAnalyzer, "run", no_browser)
    monkeypatch.setattr("api_extractor.pipeline.ExplicitGetVerifier",
                        lambda *args: ExplicitGetVerifier(*args, transport=httpx.MockTransport(handler)))

    truth_path = tmp_path / "ground_truth.json"
    truth_path.write_text(json.dumps({
        "site": "synthetic-local", "allowed_hosts": ["app.example.com"],
        "endpoints": [{"method": "GET", "path": "/api/items", "tier": "T1"}],
    }))
    truth = load_truth(truth_path)
    for run in ("run-a", "run-b"):
        directory = tmp_path / run
        directory.mkdir()
        config = directory / "site.json"
        config.write_text(json.dumps({
            "site_id": "synthetic-local", "allowed_hosts": ["app.example.com"],
            "explicit_readonly_get_urls": ["https://app.example.com/api/items"],
        }))
        code = asyncio.run(run_pipeline("https://app.example.com/", str(config),
                                        str(directory / "result.json"), 10))
        assert code == 0
    report = evaluate_pair(truth, tmp_path / "run-a", tmp_path / "run-b")
    assert len(sent) == 2 and set(sent) == {("GET", "https://app.example.com/api/items")}
    for name in ("run_a", "run_b"):
        assert report[name]["tp"] == 1 and report[name]["fp"] == 0 and report[name]["fn"] == 0
        assert report[name]["evidence_verified_tp"] == 1
        assert report[name]["objective_points_60"] == 60
    assert report["adjusted_objective_points_60"] == 60
    assert report["stability"]["endpoint_jaccard"] == 1
    assert report["stability"]["semantic_fields_identical"]


def test_v12_static_only_outputs_zero_verified_coverage(tmp_path, monkeypatch):
    monkeypatch.setattr("api_extractor.pipeline.ResourceCrawler", LocalFixtureCrawler)

    async def no_browser(self, pages):
        return []
    monkeypatch.setattr(DynamicAnalyzer, "run", no_browser)
    directory = tmp_path / "run"
    directory.mkdir()
    config = directory / "site.json"
    config.write_text(json.dumps({"site_id": "synthetic-local", "allowed_hosts": ["app.example.com"]}))
    assert asyncio.run(run_pipeline("https://app.example.com/", str(config),
                                    str(directory / "result.json"), 10)) == 0
    truth_path = tmp_path / "truth.json"
    truth_path.write_text(json.dumps({"site": "synthetic-local", "allowed_hosts": ["app.example.com"],
                                      "endpoints": [{"method": "GET", "path": "/api/items", "tier": "T1"}]}))
    result = evaluate_run(load_truth(truth_path), directory)
    assert result["tp"] == 0 and result["fn"] == 1
    assert result["objective_points_60"] == 0
    static = json.loads((directory / "static_candidates.json").read_text())
    assert static["candidates"][0]["path"] == "/api/items"
