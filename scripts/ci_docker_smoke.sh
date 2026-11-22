#!/usr/bin/env bash
# CI-only: six Chromium runs across SPA, SSR and true long-lived SSE; no external site.
# A separate synthetic out-of-scope container confirms denied requests have no side effect.
set -Eeuo pipefail
umask 077
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
IMAGE="${1:-api-extractor-ci:latest}"
FIXTURE_PY="$ROOT/tests/fixtures/docker_smoke_site.py"
[[ -f "$FIXTURE_PY" ]] || { echo 'Fixture script missing' >&2; exit 1; }
command -v docker >/dev/null || { echo 'Docker command not found' >&2; exit 1; }
command -v python3 >/dev/null || { echo 'Python3 required for verification' >&2; exit 1; }
command -v timeout >/dev/null || { echo 'timeout required' >&2; exit 1; }

tmp="$(mktemp -d "${TMPDIR:-/tmp}/api-extractor-ci.XXXXXXXX")"
network="api-ci-$(date +%s)-$$"
fixture="api-ci-site-$$"
offscope="api-ci-offscope-$$"
cleanup() {
  docker rm -f "$fixture" "$offscope" >/dev/null 2>&1 || :
  docker network rm "$network" >/dev/null 2>&1 || :
  rm -rf -- "$tmp"
}
trap cleanup EXIT

docker network create --internal "$network" >/dev/null
# Same synthetic code, different network alias: only 'fixture' is authorized.
for name in "$fixture" "$offscope"; do
  if [[ "$name" == "$fixture" ]]; then alias=fixture; else alias=offscope; fi
  docker run -d --pull=never --name "$name" --network "$network" \
    --network-alias "$alias" --read-only \
    --entrypoint python -v "$FIXTURE_PY:/site.py:ro" "$IMAGE" /site.py >/dev/null
done

for name in "$fixture" "$offscope"; do
  ready=0
  for _ in $(seq 1 30); do
    if docker exec "$name" python -c '
import urllib.request
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
assert opener.open("http://127.0.0.1:8765/", timeout=2).status == 200
' >/dev/null 2>&1; then ready=1; break; fi
    sleep 1
  done
  [[ "$ready" == 1 ]] || { echo "Isolated fixture unavailable: $name" >&2; docker logs "$name"; exit 1; }
done

printf '%s\n' '{"site_id":"ci-synthetic","allowed_hosts":["fixture"],"credentials":[],"headers":{}}' > "$tmp/site.json"
for scenario in spa ssr sse; do
  case "$scenario" in
    spa) TARGET='http://fixture:8765/'; EXPECTED='/api/items' ;;
    ssr) TARGET='http://fixture:8765/ssr'; EXPECTED='/api/ssr-items' ;;
    sse) TARGET='http://fixture:8765/sse'; EXPECTED='/api/stream' ;;
  esac
  for n in 1 2; do
    out="$tmp/$scenario-run-$n"
    mkdir -m 0777 "$out"
    # Same CLI contract as a normal benchmark run, with /out as its only write mount.
    timeout --signal=TERM --kill-after=10s 110s docker run --rm --pull=never \
      --name "api-ci-run-$scenario-$n-$$" --network "$network" \
      --user "$(id -u):$(id -g)" --read-only --shm-size=512m \
      -e HOME=/out/home -e TMPDIR=/out/tmp -e XDG_CACHE_HOME=/out/cache \
      -v "$tmp/site.json:/cfg/site.json:ro" -v "$out:/out" \
      "$IMAGE" --target "$TARGET" --config /cfg/site.json \
      --out /out/result.json --budget 90 \
      > "$out/stdout.log" 2> "$out/stderr.log" || {
      cat "$out/stderr.log" >&2; cat "$out/stdout.log" >&2; exit 1;
    }

    # Use a second container to validate with the *actual* published JSON Schema.
    docker run --rm --pull=never --network none --read-only \
      -v "$out:/out:ro" --entrypoint python "$IMAGE" -c '
import json
from pathlib import Path
from jsonschema import Draft202012Validator
root=Path("/out")
result=json.loads((root/"result.json").read_text(encoding="utf-8"))
schema=json.loads(Path("/app/api_extractor/result.schema.json").read_text(encoding="utf-8"))
errors=list(Draft202012Validator(schema).iter_errors(result))
assert not errors, "; ".join(error.message for error in errors[:3])
print("Independent JSON Schema validation PASS")
'
    python3 - "$out" "$EXPECTED" "$scenario" <<'PY'
import json
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
expected, scenario = sys.argv[2:]
result = json.loads((root / 'result.json').read_text())
rows = [json.loads(s) for s in (root / 'tool.log').read_text().splitlines() if s.strip()]
assert any(r.get('note') == 'run_status:completed' for r in rows), 'Incomplete browser run'
assert not any(r.get('method') == 'POST' for r in rows), 'Unknown POST was invoked!'
eps = result['endpoints']
assert len(eps) == 1, f'Expected exactly one real API in {scenario}, got {eps}'
ep = eps[0]
assert (ep['method'], ep['host'], ep['path']) == ('GET', 'fixture', expected), ep
assert ep['evidence'], 'API has no evidence'
if scenario == 'sse':
    assert ep.get('response', {}).get('content_type', '').startswith('text/event-stream'), (
        'SSE result must be backed by actual stream response headers')
    assert any(r.get('resource_type') == 'eventsource' and
               r.get('method') == 'GET' and r.get('status') == 200
               for r in rows), 'SSE was not observed as a browser EventSource request'
hars = [ev for ev in ep['evidence'] if ev['type'] == 'har']
assert hars, 'Static-only API incorrectly promoted to official result'
for ev in hars:
    rel = Path(ev['file'])
    assert not rel.is_absolute() and '..' not in rel.parts
    har_path = (root / rel).resolve()
    assert har_path.is_relative_to(root) and har_path.is_file()
    entries = json.loads(har_path.read_text())['log']['entries']
    idx = ev['request_index']
    assert isinstance(idx, int) and 0 <= idx < len(entries)
    entry = entries[idx]
    req = entry['request']
    assert req['method'] == 'GET' and req['url'].endswith(expected)
    assert entry['response']['status'] == 200
    assert any(r.get('phase') == 'dynamic' and r.get('request_index') == idx
               and r.get('method') == req['method'] and r.get('url') == req['url']
               and r.get('status') == entry['response']['status'] for r in rows), (
               'HAR request does not match a successful actual log request')
review = json.loads((root / 'static_candidates.json').read_text())
if scenario == 'ssr':
    assert any((r['method'], r['path']) == ('POST', '/api/submit')
               for r in review['candidates']), 'SSR form not preserved as unverified hint'
    assert not any((r['method'], r['path']) == ('POST', '/api/submit')
                   for r in eps), 'Unknown SSR form POST was promoted'
print(f'Synthetic {scenario} run passed: {len(eps)} observed API, SSR form safe')
PY
  done
  python3 - "$tmp" "$scenario" <<'PY'
import json
from pathlib import Path
import sys
base, scenario = Path(sys.argv[1]), sys.argv[2]
runs = []
for n in (1, 2):
    data = json.loads((base/f'{scenario}-run-{n}'/'result.json').read_text())
    runs.append({(e['method'],e['host'],e['path']) for e in data['endpoints']})
assert runs[0] == runs[1], f'{scenario} endpoint drift: {runs}'
print(f'{scenario} two-run stability PASS. Endpoints: {len(runs[0])}')
PY
done

# If scope filtering fails, the browser can reach this second container.
# Check its real access log, not merely a string in the scanner's own JSONL.
if docker logs "$offscope" 2>&1 | grep -E 'GET /forbidden-(resource|redirect)'; then
  echo 'SCOPE VIOLATION: out-of-scope synthetic server received a request' >&2
  exit 1
fi
echo 'Out-of-scope container saw no forbidden requests: PASS'
echo 'V17 isolated Docker acceptance PASS: SPA, SSR and SSE, 2 independent runs each'
