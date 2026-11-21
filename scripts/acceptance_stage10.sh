#!/usr/bin/env bash
# Two-run, non-destructive Docker acceptance smoke test for an authorized target.
set -Eeuo pipefail
umask 077
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
IMAGE="${API_EXTRACTOR_IMAGE:-api-extractor:0.1.0}"
NETWORK="${API_EXTRACTOR_NETWORK:-bridge}"
if [[ ${1:-} == --help || $# -lt 2 || $# -gt 3 ]]; then
  echo "Usage: bash scripts/acceptance_stage10.sh <authorized-target-url> <site.json> [budget-seconds=180]"
  echo "Requires already built image and existing Docker network; never prunes or restarts Docker."
  [[ ${1:-} == --help ]] && exit 0
  exit 2
fi
TARGET="$1"; CONFIG="$2"; BUDGET="${3:-180}"
[[ "$BUDGET" =~ ^[1-9][0-9]*$ ]] || { echo '[ERROR] Invalid budget' >&2; exit 2; }
[[ "$CONFIG" == /* ]] || CONFIG="$PWD/$CONFIG"
[[ -r "$CONFIG" && -f "$CONFIG" ]] || { echo "[ERROR] Missing config: $CONFIG" >&2; exit 2; }
CONFIG="$(realpath -e -- "$CONFIG")"
command -v docker >/dev/null || { echo '[ERROR] Docker unavailable.' >&2; exit 1; }
docker image inspect "$IMAGE" >/dev/null || { echo "[ERROR] Image missing: $IMAGE" >&2; exit 1; }
docker network inspect "$NETWORK" >/dev/null || { echo "[ERROR] Docker network missing: $NETWORK" >&2; exit 1; }
command -v python3 >/dev/null || { echo '[ERROR] Host python3 missing.' >&2; exit 1; }
python3 - "$TARGET" "$CONFIG" <<'PY'
import json,sys
from urllib.parse import urlsplit
u=urlsplit(sys.argv[1]); cfg=json.load(open(sys.argv[2],encoding='utf-8'))
assert u.scheme in ('http','https') and u.hostname and not u.username and not u.password
assert isinstance(cfg,dict) and isinstance(cfg.get('allowed_hosts'),list) and cfg['allowed_hosts'], 'Explicit allowed_hosts required'
print('[PASS] Target syntax and explicit allowlist. Authorization still requires developer confirmation.')
PY
SIZE="$(docker image inspect "$IMAGE" -f '{{.Size}}')"
if (( SIZE > 6 * 1024 * 1024 * 1024 )); then
  echo "[ERROR] Docker image exceeds 6GiB: $SIZE bytes" >&2; exit 1
fi
echo "[PASS] Image size: $SIZE bytes (<6GiB)"
STAMP="$(date +%Y%m%d_%H%M%S)_$$"
BASE="$ROOT/out/acceptance/$STAMP"
mkdir -p -- "$BASE"
ENV_ARGS=()
for name in HTTP_PROXY HTTPS_PROXY NO_PROXY http_proxy https_proxy no_proxy; do
  if [[ -n "${!name:-}" ]]; then ENV_ARGS+=(-e "$name"); fi
done
failed=0
for i in 1 2; do
  RUN="$BASE/run_$i"
  mkdir -p -- "$RUN"
  echo "[RUN] $i/2; budget ${BUDGET}s; output: $RUN"
  rc=0
  if command -v timeout >/dev/null 2>&1; then
    timeout --signal=TERM --kill-after=10s "$((BUDGET+15))" \
      docker run --rm --pull=never --network "$NETWORK" \
      --shm-size=512m --user "$(id -u):$(id -g)" \
      -e HOME=/out/home -e TMPDIR=/out/tmp -e XDG_CACHE_HOME=/out/cache "${ENV_ARGS[@]}" \
      -v "$CONFIG:/cfg/site.json:ro" -v "$RUN:/out" \
      "$IMAGE" --target "$TARGET" --config /cfg/site.json \
      --out /out/result.json --budget "$BUDGET" \
      > "$RUN/docker.stdout.log" 2> "$RUN/docker.stderr.log" || rc=$?
  else
    echo '[ERROR] timeout command required.' >&2; exit 1
  fi
  echo "$rc" > "$RUN/exit_code.txt"
  if (( rc != 0 )); then
    echo "[ERROR] Run $i exited $rc; see $RUN/docker.stderr.log" >&2
    failed=1; continue
  fi
  if ! docker run --rm --pull=never --network none \
    --entrypoint python -v "$RUN:/out:ro" "$IMAGE" -c '
import json
from pathlib import Path
from jsonschema import Draft202012Validator
root=Path("/out"); out=root/"result.json"; log=root/"tool.log"
assert out.is_file() and log.is_file() and log.stat().st_size>0, "result.json or tool.log missing"
data=json.loads(out.read_text())
schema=json.loads(Path("/app/api_extractor/result.schema.json").read_text())
errs=list(Draft202012Validator(schema).iter_errors(data))
assert not errs, "; ".join(e.message for e in errs[:3])
for raw in log.read_text().splitlines():
    row=json.loads(raw)
    assert all(x in row for x in ("method","url","status")), "invalid JSONL request row"
for ep in data["endpoints"]:
    for ev in ep["evidence"]:
        rel=Path(ev["file"])
        assert not rel.is_absolute() and ".." not in rel.parts, "unsafe evidence reference"
        path=(root/rel).resolve()
        assert path.is_relative_to(root.resolve()) and path.is_file(), "missing evidence: "+str(rel)
        if ev["type"]=="har":
            entries=json.loads(path.read_text())["log"]["entries"]
            assert 0<=ev["request_index"]<len(entries), "invalid HAR reference"
print("[PASS] Schema, JSONL, evidence verified; endpoints:",len(data["endpoints"]))
' > "$RUN/verification.log" 2>&1; then
    cat "$RUN/verification.log" >&2; failed=1
  else
    cat "$RUN/verification.log"
  fi
done
if (( failed )); then
  echo "[FAILED] Acceptance smoke checks failed. Evidence: $BASE" >&2; exit 1
fi
python3 - "$BASE" <<'PY'
import json,sys
from pathlib import Path
base=Path(sys.argv[1]); runs=[]
for i in (1,2):
    d=json.loads((base/f'run_{i}'/'result.json').read_text())
    runs.append({(ep['method'],ep['path'],ep['host']) for ep in d['endpoints']})
inter=len(runs[0]&runs[1]); union=len(runs[0]|runs[1])
score=1.0 if not union else inter/union
print(f'[RESULT] Run1={len(runs[0])}, Run2={len(runs[1])}, Jaccard={score:.3f}')
if not union: print('[WARN] Zero endpoints in both runs is not a successful API coverage test.')
print('[NOTE] Does NOT prove S1-S5 Recall/Precision, authorization or build time.')
print('[REPORT]',base)
PY
