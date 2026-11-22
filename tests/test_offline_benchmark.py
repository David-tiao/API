"""V14 benchmark is independent of browser/network execution and official scoring."""
import json
import math
from pathlib import Path

import pytest

from api_extractor.offline_benchmark import (
    _normal_path, evaluate_pair, evaluate_run, load_truth, main,
)
from api_extractor.output import build_result, write_result


TRUTH_FILE = Path(__file__).parent / "fixtures/benchmark/ground_truth.synthetic.json"


def entry(method="GET", path="/api/items", host="app.example.test", auth="none",
          evidence=None):
    return {"method": method, "path": path, "host": host, "auth": auth,
            "params": {"path": [], "query": [], "body": []},
            "evidence": evidence if evidence is not None else [
                {"type": "har", "file": "evidence/dynamic.har", "request_index": 0}],
            "confidence": 0.9, "note": "fixture evidence"}


def run_dir(root, name, endpoints, logs=None, har=None):
    out = root / name
    out.mkdir()
    write_result(out / "result.json", build_result("synthetic-offline", endpoints))
    if logs is not None:
        (out / "tool.log").write_text("".join(json.dumps(r) + "\n" for r in logs), encoding="utf-8")
    if har is not None:
        (out / "evidence").mkdir()
        (out / "evidence/dynamic.har").write_text(json.dumps({"log": {"entries": har}}))
    return out


def log_entry(method="GET", url="https://app.example.test/api/items", status=200, idx=0):
    return {"method": method, "url": url, "status": status, "phase": "dynamic", "request_index": idx}


def har_entry(method="GET", url="https://app.example.test/api/items", status=200, idx=0):
    return {"request": {"method": method, "url": url}, "response": {"status": status},
            "_requestIndex": idx, "_resourceType": "xhr"}


def test_weighted_recall_precision_and_tiers(tmp_path):
    truth = load_truth(TRUTH_FILE)
    out = run_dir(tmp_path, "one", [entry(), entry("POST", "/api/orders/123"), entry("GET", "/api/phantom")])
    score = evaluate_run(truth, out)
    assert (score["tp"], score["fp"], score["fn"]) == (2, 1, 3)
    assert score["weighted_recall"] == pytest.approx(2.0 / 7.0)
    assert score["precision"] == pytest.approx(2.0 / 3.0)
    assert score["recall_points_40"] == pytest.approx(40 * 2 / 7)
    assert score["precision_points_20"] == pytest.approx(20 * 2 / 3)
    assert score["per_tier"]["T1"]["recall"] == 1.0
    assert score["per_tier"]["T2"]["recall"] == 0.0
    assert score["per_tier"]["T3"]["recall"] == 0.0


def test_zero_output_never_gets_false_100_percent_precision(tmp_path):
    truth = load_truth(TRUTH_FILE)
    out = run_dir(tmp_path, "empty", [])
    result = evaluate_run(truth, out)
    assert result["precision"] is None
    assert result["objective_points_60"] == 0
    assert result["fn"] == 5
    assert result["evidence_rate_among_tp"] is None


def test_fp_exceeds_tp_precision_points_forfeited(tmp_path):
    out = run_dir(tmp_path, "bad", [entry(), entry(path="/wrong/a"), entry(path="/wrong/b")])
    result = evaluate_run(load_truth(TRUTH_FILE), out)
    assert (result["tp"], result["fp"]) == (1, 2)
    assert result["precision_points_20"] == 0


def test_duplicate_and_third_party_host_count_as_false_positives(tmp_path):
    out = run_dir(tmp_path, "duplicates", [entry(), entry(), entry(host="ads.other.test")])
    result = evaluate_run(load_truth(TRUTH_FILE), out)
    assert (result["tp"], result["fp"], result["duplicate_fp"], result["out_of_scope_fp"]) == (1, 2, 1, 1)


@pytest.mark.parametrize("source,expected", [
    ("/api/users/123", "/api/users/{id}"),
    ("/api/users/550e8400-e29b-41d4-a716-446655440000", "/api/users/{id}"),
    ("/api/hash/0123456789abcdef0123456789abcdef", "/api/hash/{id}"),
    ("/api/order/{orderId}", "/api/order/{id}"),
    ("/api/order/:orderId", "/api/order/{id}"),
])
def test_path_equivalence_matches_published_rules(source, expected):
    assert _normal_path(source) == expected


def test_two_run_formula_and_set_stability(tmp_path):
    truth = load_truth(TRUTH_FILE)
    a = run_dir(tmp_path, "a", [entry(), entry("POST", "/api/orders/111")])
    b = run_dir(tmp_path, "b", [entry(), entry("GQL", "/graphql")])
    result = evaluate_pair(truth, a, b)
    first, second = result["run_a"]["objective_points_60"], result["run_b"]["objective_points_60"]
    assert result["adjusted_objective_points_60"] == pytest.approx(0.7 * (first+second)/2 + 0.3 * min(first, second))
    assert result["stability"]["endpoint_jaccard"] == pytest.approx(1/3)
    assert result["official_100_point_score"] is None


def test_timestamps_and_evidence_indices_do_not_fake_instability(tmp_path):
    truth = load_truth(TRUTH_FILE)
    a = run_dir(tmp_path, "a", [entry(evidence=[{"type":"har", "file":"evidence/dynamic.har", "request_index":1}])])
    b = run_dir(tmp_path, "b", [entry(evidence=[{"type":"har", "file":"evidence/dynamic.har", "request_index":2}])])
    result = evaluate_pair(truth, a, b)
    assert result["stability"]["semantic_fields_identical"]
    assert result["stability"]["endpoint_jaccard"] == 1.0


def test_semantic_drift_detected_even_if_endpoint_keys_match(tmp_path):
    truth = load_truth(TRUTH_FILE)
    a = run_dir(tmp_path, "a", [entry(auth="none")])
    b = run_dir(tmp_path, "b", [entry(auth="bearer")])
    result = evaluate_pair(truth, a, b)
    assert result["stability"]["endpoint_jaccard"] == 1.0
    assert not result["stability"]["semantic_fields_identical"]


def test_har_and_actual_log_required_for_evidence_ratio(tmp_path):
    truth = load_truth(TRUTH_FILE)
    a = run_dir(tmp_path, "a", [entry()], logs=[log_entry()], har=[har_entry()])
    b = run_dir(tmp_path, "b", [entry()])
    result = evaluate_pair(truth, a, b)
    assert result["run_a"]["evidence_verified_tp"] == 1
    assert result["run_a"]["evidence_rate_among_tp"] == 1.0
    assert result["run_b"]["evidence_verified_tp"] == 0
    assert result["run_b"]["evidence_rate_among_tp"] == 0.0


@pytest.mark.parametrize("wrong", ["method", "path", "status", "index", "symlink"])
def test_mismatched_har_or_log_cannot_validate_evidence(tmp_path, wrong):
    truth = load_truth(TRUTH_FILE)
    record = entry()
    logs = [log_entry()]
    har = [har_entry()]
    if wrong == "method":
        har[0]["request"]["method"] = "POST"
    elif wrong == "path":
        har[0]["request"]["url"] = "https://app.example.test/api/other"
    elif wrong == "status":
        har[0]["response"]["status"] = 404
    elif wrong == "index":
        logs[0]["request_index"] = 7
    out = run_dir(tmp_path, "case", [record], logs=logs, har=har)
    if wrong == "symlink":
        external = tmp_path / "escape.har"
        (out / "evidence/dynamic.har").rename(external)
        (out / "evidence/dynamic.har").symlink_to(external)
    assert evaluate_run(truth, out)["evidence_verified_tp"] == 0


def test_log_missing_with_valid_har_is_not_proof(tmp_path):
    out = run_dir(tmp_path, "one", [entry()], har=[har_entry()])
    assert evaluate_run(load_truth(TRUTH_FILE), out)["evidence_verified_tp"] == 0


def test_ground_truth_duplicate_and_bad_tier_rejected(tmp_path):
    data = json.loads(TRUTH_FILE.read_text())
    data["endpoints"].append({"method": "GET", "path": "/api/items", "tier": "T1"})
    p = tmp_path / "truth.json"
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="duplicate"):
        load_truth(p)
    data["endpoints"].pop()
    data["endpoints"][0]["tier"] = "T8"
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="tier"):
        load_truth(p)


def test_pair_requires_independent_runs(tmp_path):
    root = run_dir(tmp_path, "one", [])
    with pytest.raises(ValueError, match="independent"):
        evaluate_pair(load_truth(TRUTH_FILE), root, root)


def test_quality_gate_fail_still_emits_report(tmp_path):
    a = run_dir(tmp_path, "a", [])
    b = run_dir(tmp_path, "b", [entry()])
    report = tmp_path / "score.json"
    status = main(["--truth", str(TRUTH_FILE), "--run-a", str(a), "--run-b", str(b),
                   "--report", str(report), "--min-recall", "0.1", "--min-jaccard", "0.8"])
    assert status == 1
    result = json.loads(report.read_text())
    assert result["quality_gate_passed"] is False
    assert result["quality_gate_failures"]
    assert result["official_100_point_score"] is None


def test_quality_gate_passes_two_identical_evidenced_runs(tmp_path):
    a = run_dir(tmp_path, "a", [entry()], logs=[log_entry()], har=[har_entry()])
    b = run_dir(tmp_path, "b", [entry()], logs=[log_entry()], har=[har_entry()])
    report = tmp_path / "report.json"
    status = main(["--truth", str(TRUTH_FILE), "--run-a", str(a), "--run-b", str(b),
                   "--report", str(report), "--min-recall", "0.1", "--min-precision", "1",
                   "--min-evidence", "1", "--min-jaccard", "1"])
    assert status == 0 and json.loads(report.read_text())["quality_gate_passed"]


def test_no_secret_copied_to_summary(tmp_path):
    a = run_dir(tmp_path, "a", [entry()])
    b = run_dir(tmp_path, "b", [entry()])
    report = evaluate_pair(load_truth(TRUTH_FILE), a, b)
    assert "Authorization" not in json.dumps(report)
    assert "generated_at" not in json.dumps(report)


def test_result_schema_must_be_valid_before_scoring(tmp_path):
    root = run_dir(tmp_path, "bad_schema", [entry()])
    data = json.loads((root / "result.json").read_text())
    del data["tool_version"]
    (root / "result.json").write_text(json.dumps(data))
    with pytest.raises(ValueError, match="schema"):
        evaluate_run(load_truth(TRUTH_FILE), root)


def test_websocket_evidence_maps_ws_to_get_handshake(tmp_path):
    expected = entry(method="WS", path="/live")
    h = har_entry(url="wss://app.example.test/live", status=101)
    h["_resourceType"] = "websocket"
    out = run_dir(tmp_path, "ws", [expected], logs=[log_entry(url="wss://app.example.test/live", status=101)], har=[h])
    result = evaluate_run(load_truth(TRUTH_FILE), out)
    assert result["tp"] == 1 and result["evidence_verified_tp"] == 1


def test_graphql_evidence_maps_gql_to_post(tmp_path):
    expected = entry(method="GQL", path="/graphql")
    h = har_entry(method="POST", url="https://app.example.test/graphql", status=200)
    out = run_dir(tmp_path, "graphql", [expected], logs=[log_entry(method="POST", url="https://app.example.test/graphql")], har=[h])
    result = evaluate_run(load_truth(TRUTH_FILE), out)
    assert result["tp"] == 1 and result["evidence_verified_tp"] == 1


def test_cli_writes_result_atomically(tmp_path):
    first = run_dir(tmp_path, "a", [entry()])
    second = run_dir(tmp_path, "b", [entry()])
    report = tmp_path / "quality.json"
    assert main(["--truth", str(TRUTH_FILE), "--run-a", str(first), "--run-b", str(second),
                 "--report", str(report)]) == 0
    assert report.is_file() and not report.with_suffix(".json.tmp").exists()


def test_site_weighted_aggregation_and_four_station_rule():
    from api_extractor.offline_benchmark import aggregate_sites
    full = {site: {"adjusted_objective_points_60": points}
            for site, points in {"S1": 10, "S2": 20, "S3": 30, "S4": 40, "S5": 50}.items()}
    five = aggregate_sites(full)
    assert five["site_weight_sum"] == 6.0
    assert five["adjusted_objective_points_60"] == pytest.approx(
        (10*1.0 + 20*1.0 + 30*1.2 + 40*1.3 + 50*1.5)/6)
    four = aggregate_sites({k: v for k, v in full.items() if k != "S1"})
    assert four["site_weight_sum"] == 5.0
    with pytest.raises(ValueError, match="S1-S5"):
        aggregate_sites({"S1": full["S1"], "S2": full["S2"]})
    with pytest.raises(ValueError, match="invalid"):
        aggregate_sites({**full, "S5": {"adjusted_objective_points_60": 61}})


def test_evidence_ratio_is_measured_over_all_outputs(tmp_path):
    a = run_dir(tmp_path, "a", [entry(), entry(path="/wrong")],
                logs=[log_entry()], har=[har_entry()])
    result = evaluate_run(load_truth(TRUTH_FILE), a)
    assert result["evidence_verified_outputs"] == 1
    assert result["evidence_rate_all_outputs"] == 0.5
    assert result["evidence_rate_among_tp"] == 1.0
