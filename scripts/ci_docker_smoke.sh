#!/usr/bin/env bash
# CI-only: two real Chromium runs against an isolated synthetic HTTP target.
# Never tests external sites, prunes Docker globally or touches other containers.
set -Eeuo pipefail
umask 077
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
IMAGE="${1:-api-extractor-ci:latest}"
FIXTURE_PY="$ROOT/tests/fixtures/docker_smoke_site.py"
[[ -f "$FIXTURE_PY" ]] || { echo 'Fixture script missing' >&2; exit 1; }
command -v docker >/dev/null || { echo 'Docker command not found' >&2; exit 1; }
command -v python3 >/dev/null || { echo 'Python3 required for validation' >&2; exit 1; }

tmp="$(mktemp -d "${TMPDIR:-/tmp}/api-extractor-ci.XXXXXXXX")"
network="api-ci-$(date +%s)-$$"
fixture="api-ci-site-$$"
cleanup() {
  docker rm -f "$fixture" >/dev/null 2>&1 || :
  docker network rm "$network" >/dev/null 2>&1 || :
  rm -rf -- "$tmp"
}
trap cleanup EXIT

docker network create --internal "$network" >/dev/null
# Reuse the built image, avoid downloading any unrelated fixture image.
docker run -d --pull=never --name "$fixture" --network "$network" \
  --network-alias fixture --read-only \
  --entrypoint python -v "$FIXTURE_PY:/site.py:ro" "$IMAGE" /site.py >/dev/null

# Health check runs inside this fixture container; no Internet needed.
ready=0
for _ in $(seq 1 30); do
  if docker exec "$fixture" python -c '
import urllib.request
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
assert opener.open("http://127.0.0.1:8765/", timeout=2).status == 200
' >/dev/null 2>&1; then ready=1; break; fi
  sleep 1
done
[[ "$ready" == 1 ]] || { echo 'Isolated fixture did not become ready' >&2; docker logs "$fixture"; exit 1; }

printf '%s\n' '{"site_id":"ci-synthetic","allowed_hosts":["fixture"],"credentials":[],"headers":{}}' > "$tmp/site.json"
for n in 1 2; do
  out="$tmp/run-$n"
  mkdir -m 0777 "$out"
  # An internal-only Docker network blocks all traffic outside the fixture network.
  # Read-only container root also catches common non-/out write attempts.
  timeout --signal=TERM --kill-after=10s 110s docker run --rm --pull=never \
    --name "api-ci-run-$n-$$" --network "$network" --user "$(id -u):$(id -g)" \
    --read-only --shm-size=512m \
    -e HOME=/out/home -e TMPDIR=/out/tmp -e XDG_CACHE_HOME=/out/cache \
    -v "$tmp/site.json:/cfg/site.json:ro" -v "$out:/out" \
    "$IMAGE" --target http://fixture:8765/ --config /cfg/site.json \
    --out /out/result.json --budget 90 \
    > "$out/stdout.log" 2> "$out/stderr.log" || {
    cat "$out/stderr.log" >&2; cat "$out/stdout.log" >&2; exit 1;
  }
  python3 - "$out" <<'PY'
import json
from pathlib import Path
import sys
p = Path(sys.argv[1]); result = json.loads((p/'result.json').read_text())
assert result['endpoints'], 'No observed endpoints: browser may not have run'
eps=[e for e in result['endpoints'] if e['method']=='GET' and e['path']=='/api/items']
assert eps, 'Missing real network-observed GET /api/items'
log=[json.loads(s) for s in (p/'tool.log').read_text().splitlines() if s.strip()]
assert any(row.get('method')=='GET' and row.get('url','').endswith('/api/items')
           and row.get('status')==200 for row in log), 'No actual API request in tool.log'
assert any(row.get('note')=='run_status:completed' for row in log), 'Run not marked completed'
for ep in eps:
    evidence=[ev for ev in ep['evidence'] if ev.get('type')=='har']
    assert evidence, 'A verified endpoint must have HAR evidence'
    for ev in evidence:
        rel=Path(ev['file']); assert not rel.is_absolute() and '..' not in rel.parts
        f=(p/rel).resolve(); assert f.is_relative_to(p.resolve()) and f.is_file()
        entries=json.loads(f.read_text())['log']['entries']
        req=entries[ev['request_index']]['request']
        assert req['method']=='GET' and req['url'].endswith('/api/items')
print('Synthetic run passed:', len(result['endpoints']), 'endpoints')
PY
done
python3 - "$tmp" <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1]); rows=[]
for n in (1,2):
    d=json.loads((root/f'run-{n}'/'result.json').read_text())
    rows.append({(e['method'],e['host'],e['path']) for e in d['endpoints']})
assert rows[0] == rows[1], f'Two-run endpoint sets drifted: {rows}'
print('Two-run Docker smoke PASS. Stable endpoint count:',len(rows[0]))
PY
