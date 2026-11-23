#!/usr/bin/env bash
# Independent read-only API discovery on a self-hosted OWASP Juice Shop instance.
# NEVER scan the public demo. This lab is confined to an internal Docker network.
set -Eeuo pipefail
umask 077
command -v docker >/dev/null
command -v python3 >/dev/null
command -v timeout >/dev/null

APP_IMAGE="bkimminich/juice-shop:latest"
SCANNER_IMAGE="api-extractor-juice-lab:latest"
tmp="$(mktemp -d)"
net="juice-api-lab-$(date +%s)-$$"
app="juice-app-$$"
cleanup() {
  docker rm -f "$app" >/dev/null 2>&1 || :
  docker network rm "$net" >/dev/null 2>&1 || :
  rm -rf "$tmp"
}
trap cleanup EXIT

docker network create --internal "$net" >/dev/null
# No -p / --publish: the intentionally vulnerable application is never reachable
# from outside the isolated lab network.
docker run -d --pull=never --name "$app" --network "$net" \
  --network-alias juice-shop "$APP_IMAGE" >/dev/null
ready=0
for _ in $(seq 1 180); do
  # Juice Shop performs optional external-dependency checks on startup.
  # Its own boot completion marker is more reliable inside a no-egress lab.
  if docker logs "$app" 2>&1 | grep -q 'Server listening on port 3000'; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "$ready" != 1 ]]; then
  echo "Juice Shop lab did not become healthy" >&2
  docker logs "$app" 2>&1 | tail -35 >&2
  docker inspect "$app" --format 'Container state: {{.State.Status}}' >&2 || :
  exit 1
fi
echo "Self-hosted Juice Shop ready: internal Docker network only."
echo "Checking Juice Shop HTTP through the scanner's isolated Docker network:"
docker run --rm --pull=never --network "$net" --read-only \
  --entrypoint python "$SCANNER_IMAGE" -c '
import urllib.request
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open("http://juice-shop:3000/", timeout=12) as r:
    print("Lab HTTP status:", r.status, "content type:", r.headers.get("Content-Type"))
'

docker image inspect "$APP_IMAGE" --format 'Juice Shop image ID: {{.Id}}'

cat > "$tmp/site.json" <<'JSON'
{
  "site_id": "selfhosted-owasp-juice-shop",
  "allowed_hosts": ["juice-shop"],
  "credentials": [],
  "headers": {},
  "notes": "Own isolated OWASP Juice Shop lab; read-only authorized browser discovery"
}
JSON

for n in 1 2; do
  out="$tmp/run-$n"
  mkdir -m 0777 "$out"
  echo "Starting independent Juice Shop scan $n/2"
  timeout --signal=TERM --kill-after=10s 160s docker run --rm --pull=never \
    --name "juice-scanner-$n-$$" --network "$net" \
    --user "$(id -u):$(id -g)" --read-only --shm-size=512m \
    -e HOME=/out/home -e TMPDIR=/out/tmp -e XDG_CACHE_HOME=/out/cache \
    -v "$tmp/site.json:/cfg/site.json:ro" -v "$out:/out" \
    "$SCANNER_IMAGE" \
    --target http://juice-shop:3000/ --config /cfg/site.json \
    --out /out/result.json --budget 120 \
    > "$out/stdout.log" 2> "$out/stderr.log" || {
      echo "Scanner returned nonzero on run $n" >&2
      tail -80 "$out/stderr.log" >&2 || :
      tail -40 "$out/stdout.log" >&2 || :
      exit 1
    }
  python3 - "$out" "$n" <<'DIAG'
import json
from pathlib import Path
import sys
out, n = Path(sys.argv[1]), sys.argv[2]
result = json.loads((out / "result.json").read_text())
records = [json.loads(line) for line in (out / "tool.log").read_text().splitlines()
           if line.strip()]
notes = [r.get("note") for r in records if isinstance(r.get("note"), str)]
print("Run", n, "diagnosis:", "endpoints", len(result.get("endpoints", [])),
      "log lines", len(records), "last notes", notes[-15:])
DIAG
  # Validate the actual published output schema, in a separate offline container.
  docker run --rm --pull=never --network none --read-only \
    -v "$out:/out:ro" --entrypoint python "$SCANNER_IMAGE" -c '
import json
from pathlib import Path
from jsonschema import Draft202012Validator
result = json.loads(Path("/out/result.json").read_text())
schema = json.loads(Path("/app/api_extractor/result.schema.json").read_text())
errors = list(Draft202012Validator(schema).iter_errors(result))
assert not errors, "; ".join(error.message for error in errors[:3])
print("Independent result.json schema PASS")
'
done

mkdir -p "$GITHUB_WORKSPACE/lab-output"
python3 - "$tmp" "$GITHUB_WORKSPACE/lab-output/summary.json" <<'PY'
from __future__ import annotations

import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
destination = Path(sys.argv[2])
snapshots = []
for n in (1, 2):
    out = root / f"run-{n}"
    result = json.loads((out / "result.json").read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in (out / "tool.log").read_text(encoding="utf-8").splitlines()
            if line.strip()]
    assert set(result) >= {"site", "generated_at", "tool_version", "endpoints"}
    completed = any(row.get("note") == "run_status:completed" for row in rows)
    assert all(row.get("phase") in {"static", "dynamic", "verify"} for row in rows), (
        f"Run {n}: bad public log phase")
    endpoints = result["endpoints"]
    assert isinstance(endpoints, list)
    observed = {
        (row.get("method"), row.get("url"), row.get("status"), row.get("request_index"))
        for row in rows if row.get("phase") == "dynamic"
        and row.get("detail_phase") != "redirect"
    }
    confirmed = 0
    for endpoint in endpoints:
        assert endpoint["host"] == "juice-shop", (
            f"Run {n}: endpoint host escaped the allowlist")
        har_refs = [ev for ev in endpoint.get("evidence", []) if ev.get("type") == "har"]
        assert har_refs, f"Run {n}: reported API missing actual HAR proof"
        for ev in har_refs:
            relative = Path(ev["file"])
            assert not relative.is_absolute() and ".." not in relative.parts
            path = (out / relative).resolve(strict=True)
            assert path.is_relative_to(out.resolve())
            entries = json.loads(path.read_text(encoding="utf-8"))["log"]["entries"]
            idx = ev["request_index"]
            assert isinstance(idx, int) and not isinstance(idx, bool) and 0 <= idx < len(entries)
            entry = entries[idx]
            request = entry["request"]
            status = entry["response"]["status"]
            assert (request["method"], request["url"], status, idx) in observed, (
                f"Run {n}: HAR and JSONL do not prove the same concrete request")
        confirmed += 1
    fingerprint = sorted({(e["method"], e["host"], e["path"]) for e in endpoints})
    snapshot = {
        "run": n,
        "complete": completed,
        "api_count": len(endpoints),
        "har_proven_count": confirmed,
        "api_fingerprint": [list(item) for item in fingerprint],
        "dynamic_log_records": sum(row.get("phase") == "dynamic" for row in rows),
    }
    snapshots.append(snapshot)
    print(f"Juice Shop run {n}: {len(endpoints)} APIs; {confirmed} HAR-backed;"
          f" {snapshot['dynamic_log_records']} dynamic log records")
    for method, host, path in fingerprint[:20]:
        print(f"  {method} {host}{path}")

first, second = (set(map(tuple, snap["api_fingerprint"])) for snap in snapshots)
intersection = len(first & second)
union = len(first | second)
jaccard = intersection / union if union else 1.0
summary = {
    "lab": "self-hosted OWASP Juice Shop (isolated network, no published ports)",
    "reference_scanner_commit": "6608f206dba7ba2543f117d7d5c9a749eab9fa8e",
    "runs": snapshots,
    "two_run_jaccard": round(jaccard, 4),
    "both_runs_nonempty": all(s["api_count"] > 0 for s in snapshots),
    "both_runs_complete": all(s["complete"] for s in snapshots),
    "official_hidden_evaluation": False,
}
destination.write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(f"Juice Shop two-run Jaccard: {jaccard:.4f}")
if not summary["both_runs_nonempty"]:
    raise SystemExit("FAIL: zero evidence-backed API endpoints in one of the runs")
if not summary["both_runs_complete"]:
    raise SystemExit("FAIL: browser phase incomplete; see lab summary and run diagnostics")
PY

echo "Independent Juice Shop acceptance completed."
