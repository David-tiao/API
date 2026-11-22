"""Deterministic, offline, evidence-aware *partial* scoring for Topic B.

This is a development harness, not the organizer's hidden evaluator. It does
not access the network and never changes result.json or the saved evidence.
Only the objective Recall(40) and Precision(20) portions are scored. The
remaining Semantic(20), Evidence(10) and Engineering(10) official points are
not fabricated by this tool.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator

TIER_WEIGHT = {"T1": 1.0, "T2": 1.4, "T3": 1.8}
SITE_WEIGHT = {"S1": 1.0, "S2": 1.0, "S3": 1.2, "S4": 1.3, "S5": 1.5}
ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "WS", "GQL"}
_NUMERIC = re.compile(r"^\d+$")
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I)
_HEX = re.compile(r"^[0-9a-f]{16,}$", re.I)
MAX_RESULT_BYTES = 16 * 1024 * 1024
MAX_LOG_BYTES = 32 * 1024 * 1024
SCHEMA_FILE = Path(__file__).with_name("result.schema.json")


def _normal_path(path: str) -> str:
    """Independent reference implementation of the published path rule."""
    if not isinstance(path, str) or not path.startswith("/") or "?" in path or "#" in path:
        raise ValueError("benchmark paths must be absolute, query-free paths")
    parts = []
    for segment in path.split("/"):
        if not segment:
            continue
        if (segment.startswith(":") or (segment.startswith("{") and segment.endswith("}"))
                or _NUMERIC.fullmatch(segment) or _UUID.fullmatch(segment) or _HEX.fullmatch(segment)):
            parts.append("{id}")
        else:
            parts.append(segment)
    return "/" + "/".join(parts)


def _identity(row: dict) -> tuple[str, str]:
    method = str(row.get("method", "")).upper()
    if method not in ALLOWED_METHODS:
        raise ValueError(f"invalid API method {method!r}")
    return method, _normal_path(row.get("path", ""))


def _load_json(path: Path, limit: int = MAX_RESULT_BYTES) -> dict:
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError(f"missing or overlarge benchmark input: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON input: {path}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"input must be a JSON object: {path}")
    return data


def load_truth(path: str | Path) -> dict:
    """Validate fixed synthetic ground truth; no site-specific production logic."""
    truth = _load_json(Path(path))
    allowed = truth.get("allowed_hosts")
    rows = truth.get("endpoints")
    if (not isinstance(truth.get("site"), str) or not truth["site"]
            or not isinstance(allowed, list) or not allowed
            or not all(isinstance(h, str) and h and h == h.lower() for h in allowed)
            or not isinstance(rows, list) or not (0 < len(rows) <= 10000)):
        raise ValueError("truth requires site, allowed_hosts and a nonempty endpoints array")
    keys = set()
    for row in rows:
        if not isinstance(row, dict) or row.get("tier") not in TIER_WEIGHT:
            raise ValueError("each truth row needs a supported T1/T2/T3 tier")
        key = _identity(row)
        if key in keys:
            raise ValueError(f"duplicate ground-truth method/path: {key}")
        keys.add(key)
    return truth


def _inside(root: Path, name: object) -> Path | None:
    if not isinstance(name, str) or not name:
        return None
    rel = Path(name)
    if rel.is_absolute() or ".." in rel.parts:
        return None
    try:
        candidate = (root / rel).resolve(strict=True)
        if candidate.is_relative_to(root) and candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    except (OSError, ValueError):
        pass
    return None


def _observed_log(root: Path) -> set[tuple[str, str, str, int, int]]:
    log = _inside(root, "tool.log")
    if log is None:
        return set()
    if log.stat().st_size > MAX_LOG_BYTES:
        raise ValueError("benchmark tool.log is too large")
    observed = set()
    with log.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            try:
                row = json.loads(line)
                if row.get("phase") not in {"dynamic", "probe"}:
                    continue
                if row.get("phase") == "probe" and row.get("resource_type") != "explicit_safe_get":
                    continue
                url = urlsplit(str(row.get("url", "")))
                index = row.get("request_index")
                status = int(row.get("status", 0))
                if (not url.hostname or not isinstance(index, int) or isinstance(index, bool)
                        or status < 100 or (status >= 400 and status not in {401, 403})):
                    continue
                observed.add((str(row.get("method", "")).upper(), url.hostname.lower(),
                              _normal_path(url.path or "/"), index, status))
            except (ValueError, TypeError, AttributeError):
                continue
    return observed


def _har_proof(row: dict, root: Path, observed: set, cache: dict[Path, list]) -> bool:
    """Independent cross-check of HAR to real per-run JSONL request evidence."""
    for evidence in row.get("evidence", []):
        if not isinstance(evidence, dict) or evidence.get("type") != "har":
            continue
        index = evidence.get("request_index")
        path = _inside(root, evidence.get("file"))
        if path is None or not isinstance(index, int) or isinstance(index, bool):
            continue
        try:
            if path not in cache:
                candidate = _load_json(path, MAX_LOG_BYTES)["log"]["entries"]
                if not isinstance(candidate, list):
                    continue
                cache[path] = candidate
            entries = cache[path]
            if not isinstance(entries, list) or not 0 <= index < len(entries):
                continue
            entry = entries[index]
            request, response = entry["request"], entry["response"]
            if entry.get("_requestIndex", index) != index:
                continue
            url = urlsplit(request["url"])
            if not url.hostname:
                continue
            wire_method = str(request["method"]).upper()
            declared_method = str(row["method"]).upper()
            if declared_method == "WS":
                if wire_method != "GET" or entry.get("_resourceType") != "websocket":
                    continue
            elif declared_method == "GQL":
                if wire_method not in {"GET", "POST"}:
                    continue
            elif declared_method != wire_method:
                continue
            status = int(response["status"])
            if (_normal_path(url.path or "/") != _normal_path(row["path"])
                    or url.hostname.lower() != row["host"].lower()):
                continue
            if (wire_method, url.hostname.lower(), _normal_path(url.path or "/"),
                    index, status) in observed:
                return True
        except (KeyError, TypeError, IndexError, ValueError, AttributeError):
            continue
    return False


def _stable_payload(endpoints: list[dict]) -> str:
    """Ignore generated_at and volatile evidence indexing, not semantic drift."""
    fields = ("method", "host", "path", "auth", "params", "response", "note")
    subset = [{key: row[key] for key in fields if key in row} for row in endpoints]
    canonical = json.dumps(sorted(subset, key=lambda r: json.dumps(r, sort_keys=True)),
                           sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def evaluate_run(truth: dict, directory: str | Path) -> dict:
    """Score objectively observable parts of a single local run (out of 60)."""
    directory = Path(directory).resolve(strict=True)
    result = _load_json(directory / "result.json")
    if result.get("site") != truth["site"] or not isinstance(result.get("endpoints"), list):
        raise ValueError("result.site differs from truth.site or endpoints is missing")
    schema = _load_json(SCHEMA_FILE)
    errors = list(Draft202012Validator(schema).iter_errors(result))
    if errors:
        raise ValueError(f"result.json violates the output schema: {errors[0].message}")
    rows = result["endpoints"]
    if len(rows) > 20000:
        raise ValueError("too many output endpoints for offline evaluation")
    truth_keys = {_identity(row): row["tier"] for row in truth["endpoints"]}
    allowed_hosts = set(truth["allowed_hosts"])
    seen: set[tuple[str, str]] = set()
    tp, fp, duplicate, invalid_host = set(), 0, 0, 0
    evidence_valid = 0
    output_proven = 0
    evidence_seen = _observed_log(directory)
    har_cache: dict[Path, list] = {}
    keys = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("host"), str):
            raise ValueError("malformed output endpoint")
        key = _identity(row)
        host_ok = row["host"].lower() in allowed_hosts
        keys.append((row["host"].lower(), *key))
        has_proof = _har_proof(row, directory, evidence_seen, har_cache)
        if has_proof:
            output_proven += 1
        if not host_ok:
            invalid_host += 1
            fp += 1
        elif key in seen:
            duplicate += 1
            fp += 1
        elif key in truth_keys:
            tp.add(key)
            if has_proof:
                evidence_valid += 1
        else:
            fp += 1
        if host_ok:
            seen.add(key)
    fn = set(truth_keys) - tp
    hit_weight = sum(TIER_WEIGHT[truth_keys[key]] for key in tp)
    total_weight = sum(TIER_WEIGHT[t] for t in truth_keys.values())
    recall = hit_weight / total_weight
    precision = len(tp) / (len(tp) + fp) if len(tp) + fp else None
    recall_points = 40.0 * recall
    precision_points = 0.0 if precision is None or fp > len(tp) else 20.0 * precision
    by_tier = {}
    for tier in TIER_WEIGHT:
        expected = sum(t == tier for t in truth_keys.values())
        matched = sum(truth_keys[key] == tier for key in tp)
        by_tier[tier] = {"tp": matched, "ground_truth": expected,
                         "recall": matched / expected if expected else None}
    return {
        "tp": len(tp), "fp": fp, "fn": len(fn), "duplicate_fp": duplicate,
        "out_of_scope_fp": invalid_host, "weighted_recall": recall, "precision": precision,
        "recall_points_40": recall_points, "precision_points_20": precision_points,
        "objective_points_60": recall_points + precision_points,
        "evidence_verified_tp": evidence_valid,
        "evidence_verified_outputs": output_proven,
        "evidence_rate_all_outputs": output_proven / len(rows) if rows else None,
        "evidence_rate_among_tp": evidence_valid / len(tp) if tp else None,
        "per_tier": by_tier,
        "matched": [list(k) for k in sorted(tp)],
        "missed": [list(k) for k in sorted(fn)],
        "predicted_keys": [list(k) for k in sorted(set(keys))],
        "semantic_fingerprint": _stable_payload(rows),
    }


def evaluate_pair(truth: dict, run_a: str | Path, run_b: str | Path) -> dict:
    """Two-run stability adjustment on *partial 60-point* objective metrics."""
    if Path(run_a).resolve() == Path(run_b).resolve():
        raise ValueError("two independent run directories are required")
    a = evaluate_run(truth, run_a)
    b = evaluate_run(truth, run_b)
    first = set(map(tuple, a["predicted_keys"]))
    second = set(map(tuple, b["predicted_keys"]))
    overlap = len(first & second)
    union = len(first | second)
    x, y = a["objective_points_60"], b["objective_points_60"]
    return {
        "site": truth["site"], "local_only": True,
        "official_100_point_score": None,
        "missing_official_dimensions": ["semantic_20", "evidence_10", "engineering_10"],
        "run_a": a, "run_b": b,
        "stability": {
            "endpoint_jaccard": overlap / union if union else 1.0,
            "semantic_fields_identical": a["semantic_fingerprint"] == b["semantic_fingerprint"],
            "only_a": [list(k) for k in sorted(first - second)],
            "only_b": [list(k) for k in sorted(second - first)],
        },
        "adjusted_objective_points_60": 0.7 * ((x + y) / 2) + 0.3 * min(x, y),
    }


def aggregate_sites(reports: dict[str, dict]) -> dict:
    """Published site weights on partial 60-point objectives, not official totals.

    Four-site mode excludes S1. Prevent silent omission of any other station.
    """
    selected = set(reports)
    full = set(SITE_WEIGHT)
    if selected != full and selected != full - {"S1"}:
        raise ValueError("offline site aggregation requires S1-S5, or S2-S5 only")
    for site, report in reports.items():
        score = report.get("adjusted_objective_points_60")
        if (not isinstance(score, (int, float)) or isinstance(score, bool)
                or not 0 <= score <= 60 or score != score):
            raise ValueError(f"site {site} has invalid partial objective points")
    denominator = sum(SITE_WEIGHT[site] for site in selected)
    return {
        "included_sites": sorted(selected),
        "site_weight_sum": denominator,
        "adjusted_objective_points_60": sum(
            SITE_WEIGHT[s] * reports[s]["adjusted_objective_points_60"] for s in selected
        ) / denominator,
        "official_100_point_score": None,
    }


def main(argv: list[str] | None = None) -> int:
    """Offline command: python -m api_extractor.offline_benchmark ..."""
    import argparse
    parser = argparse.ArgumentParser(description="Local synthetic benchmark; no network and no official score")
    parser.add_argument("--truth", required=True)
    parser.add_argument("--run-a", required=True)
    parser.add_argument("--run-b", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--min-recall", type=float)
    parser.add_argument("--min-precision", type=float)
    parser.add_argument("--min-evidence", type=float)
    parser.add_argument("--min-jaccard", type=float)
    args = parser.parse_args(argv)
    for label in ("min_recall", "min_precision", "min_evidence", "min_jaccard"):
        value = getattr(args, label)
        if value is not None and not 0 <= value <= 1:
            parser.error(f"--{label.replace('_', '-')} must be between 0 and 1")
    truth = load_truth(args.truth)
    report = evaluate_pair(truth, args.run_a, args.run_b)
    failed = []
    for label, field in (("recall", "weighted_recall"), ("precision", "precision"),
                         ("evidence", "evidence_rate_among_tp")):
        threshold = getattr(args, "min_" + label)
        if threshold is not None:
            for run_name in ("run_a", "run_b"):
                value = report[run_name][field]
                if value is None or value < threshold:
                    failed.append(f"{run_name}.{field} below {threshold}")
    if args.min_jaccard is not None and report["stability"]["endpoint_jaccard"] < args.min_jaccard:
        failed.append("stability.endpoint_jaccard below minimum")
    report["quality_gate_passed"] = not failed
    report["quality_gate_failures"] = failed
    path = Path(args.report)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    print(f"local objective score: {report['adjusted_objective_points_60']:.2f}/60; "
          f"jaccard: {report['stability']['endpoint_jaccard']:.3f}; "
          f"gates: {'PASS' if not failed else 'FAIL'}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
