#!/usr/bin/env bash
# API Extractor Stage 10: diagnostics; no sudo, destructive cleanup, or silent installs.
set -Eeuo pipefail
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
OPS_DIR="$ROOT_DIR/out/operations"
IMAGE="${API_EXTRACTOR_IMAGE:-api-extractor:0.1.0}"
MODE="${1:-check}"
shift || true
DO_BUILD=0
DO_TEST=0
VERBOSE=0
for arg in "$@"; do
  case "$arg" in
    --build) DO_BUILD=1 ;;
    --test) DO_TEST=1 ;;
    --verbose) VERBOSE=1 ;;
    --no-install) : ;;  # Always no-install by default.
    *) printf '[ERROR] Unknown option: %s\n' "$arg" >&2; exit 2 ;;
  esac
done

usage() {
  cat <<'HELP'
Usage:
  bash scripts/diagnose_environment_stage10.sh check [--build] [--test] [--verbose]
  bash scripts/diagnose_environment_stage10.sh env
  bash scripts/diagnose_environment_stage10.sh deps
  bash scripts/diagnose_environment_stage10.sh build
  bash scripts/diagnose_environment_stage10.sh test
  bash scripts/diagnose_environment_stage10.sh report
  bash scripts/diagnose_environment_stage10.sh logs

Default check is read-only apart from writing diagnostics under out/operations/.
--build / build explicitly builds a Docker image (may download dependencies).
--test runs existing unit tests in the image without altering project sources.
No apt/sudo/systemctl/prune/force-remove is performed.
HELP
}
[[ "$MODE" =~ ^(check|env|deps|build|test|report|logs|help|-h|--help)$ ]] || { usage; exit 2; }
if [[ "$MODE" == help || "$MODE" == -h || "$MODE" == --help ]]; then usage; exit 0; fi
if [[ "$MODE" == report ]]; then
  [[ -f "$OPS_DIR/diagnosis_latest.json" ]] || { echo '[WARN] No previous report.'; exit 1; }
  cat "$OPS_DIR/diagnosis_latest.json"; exit 0
fi
if [[ "$MODE" == logs ]]; then
  [[ -f "$OPS_DIR/diagnosis_latest.log" ]] || { echo '[WARN] No previous diagnostic log.'; exit 1; }
  tail -n 100 "$OPS_DIR/diagnosis_latest.log"; exit 0
fi

mkdir -p "$OPS_DIR"
command -v flock >/dev/null 2>&1 || { echo '[ERROR] flock (util-linux) required.' >&2; exit 1; }
# One diagnostic build at a time; same lock is used by the startup script.
exec 9>"$OPS_DIR/lifecycle.lock"
flock -n 9 || { echo '[ERROR] API Extractor lifecycle/build operation already in progress.' >&2; exit 1; }
RUN_ID="$(date +%Y%m%d_%H%M%S)_$$"
LOG="$OPS_DIR/diagnosis_${RUN_ID}.log"
REPORT="$OPS_DIR/diagnosis_${RUN_ID}.json"
ISSUES="$OPS_DIR/diagnosis_${RUN_ID}.issues"
: > "$LOG"
: > "$ISSUES"
PASS=0 WARN=0 FAIL=0 INCOMPLETE=0
log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG"; }
pass() { PASS=$((PASS+1)); log "[PASS] $*"; }
warn() { WARN=$((WARN+1)); log "[WARN] $*"; }
fail() { FAIL=$((FAIL+1)); log "[ERROR] $*"; printf '%s\n' "$*" >> "$ISSUES"; }
unknown() { INCOMPLETE=$((INCOMPLETE+1)); log "[UNVERIFIED] $*"; }
have_image() { docker image inspect "$IMAGE" >/dev/null 2>&1; }
have_docker() { command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; }

report_finish() {
  local code="${1:-0}" result=PASS
  if (( FAIL > 0 )); then result=FAILED
  elif (( INCOMPLETE > 0 )); then result=INCOMPLETE
  elif (( WARN > 0 )); then result=PASS_WITH_WARNINGS
  fi
  command -v python3 >/dev/null 2>&1 && python3 - "$REPORT" "$MODE" "$result" "$PASS" "$WARN" "$FAIL" "$INCOMPLETE" "$LOG" "$ISSUES" "$IMAGE" <<'PY' || true
import json,sys,datetime,platform
from pathlib import Path
out,mode,result,p,w,f,u,log,issues,image=sys.argv[1:]
data={
 'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'project':'API Extractor','mode':mode,'status':result,
 'system':{'platform':platform.platform(), 'architecture':platform.machine()},
 'image':image,'counts':{'pass':int(p),'warn':int(w),'fail':int(f),'unverified':int(u)},
 'issues':[x.strip() for x in Path(issues).read_text().splitlines() if x.strip()],
 'full_log':str(Path(log).resolve()),
 'notes':['Docker build, syntax check, CLI check and real extraction are different verification levels.',
          'Full S1-S5 end-to-end extraction on the user machine is not claimed.']}
Path(out).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
PY
  log "[SUMMARY] PASS=$PASS WARN=$WARN ERROR=$FAIL UNVERIFIED=$INCOMPLETE RESULT=$result"
  log "[REPORT] $REPORT"
  if [[ -f "$REPORT" ]]; then
    cp "$REPORT" "$OPS_DIR/diagnosis_latest.json"
  fi
  cp "$LOG" "$OPS_DIR/diagnosis_latest.log"
  (( FAIL == 0 && code == 0 )) || return 1
  return 0
}
trap 'log "[ERROR] Interrupted; see preserved log $LOG" >&2' INT TERM

check_os() {
  log '[CHECK] OS, storage, Docker daemon...'
  if [[ -r /etc/os-release ]]; then
    # Read only standard host metadata.
    . /etc/os-release
    log "[INFO] Host OS: ${PRETTY_NAME:-unknown}"
  else
    warn '/etc/os-release unavailable.'
  fi
  log "[INFO] Kernel: $(uname -r); arch: $(uname -m); user: $(id -un)"
  log "[INFO] Project: $ROOT_DIR"
  if [[ "$(uname -s)" != Linux ]]; then fail 'Linux required for this script.'; else pass 'Linux platform.'; fi
  if command -v python3 >/dev/null 2>&1; then
    log "[INFO] Host Python: $(python3 --version 2>&1) (not required to be >=3.11 for Docker mode)"
    pass 'Host Python available for report generation.'
  else
    unknown 'Host Python3 missing; structured JSON report may not be generated.'
  fi
  if ! command -v docker >/dev/null 2>&1; then
    fail 'Docker command not found.'; return
  fi
  log "[INFO] Docker client: $(docker --version 2>&1)"
  if have_docker; then pass 'Docker daemon accessible.'
  else fail 'Docker daemon unavailable or permission denied; check docker info.'; return
  fi
  local freekb
  freekb="$(df -Pk "$ROOT_DIR" | awk 'NR==2{print $4}')"
  [[ "$freekb" =~ ^[0-9]+$ ]] || freekb=0
  log "[INFO] Free disk (KB): $freekb"
  if (( freekb < 5242880 )); then warn 'Less than 5 GiB free; browser image builds may fail.'
  else pass 'At least 5 GiB free.'; fi
}
check_files() {
  log '[CHECK] Project files...'
  local f found=0
  for f in Dockerfile README.md requirements.txt package.json package-lock.json api_extractor/cli.py api_extractor/pipeline.py api_extractor/result.schema.json; do
    if [[ ! -f "$ROOT_DIR/$f" ]]; then fail "Required file missing: $f"; found=1; fi
  done
  if (( found == 0 )); then pass 'All core project files present.'; fi
  if [[ -d "$ROOT_DIR/tests" ]]; then pass 'tests directory exists.'
  else warn 'tests directory absent.'; fi
  # Syntax-check shell without executing them.
  if bash -n "$SCRIPT_DIR/start_safe_stage8.sh" "$SCRIPT_DIR/diagnose_environment_stage10.sh"; then
    pass 'Shell syntax check passed.'
  else
    fail 'Shell syntax check failed.'
  fi
}
check_deps() {
  log '[CHECK] Docker image, Python/Node dependencies, CLI...'
  if ! have_docker; then fail 'Docker unavailable; cannot check image dependencies.'; return; fi
  if ! have_image; then
    fail "Image missing: $IMAGE; run diagnose_environment_stage10.sh build."
    return
  fi
  pass "Docker image exists: $IMAGE"
  if docker run --rm --pull=never --entrypoint python "$IMAGE" -c '
import importlib.metadata as m
import re
from pathlib import Path
checks=0
for raw in Path("/app/requirements.txt").read_text().splitlines():
    line=raw.strip()
    if not line or line.startswith("#"): continue
    match=re.fullmatch(r"([A-Za-z0-9_.-]+)==([^;\s]+)",line)
    if not match:
        raise SystemExit("Unsupported/unlocked requirement: " + line)
    name,expected=match.groups()
    actual=m.version(name)
    print(name,actual,"required",expected)
    if actual!=expected:
        raise SystemExit("Dependency version mismatch: " + name)
    checks+=1
assert checks>0,"No requirements checked"
' 2>&1 | tee -a "$LOG"; then
    pass 'Container Python dependencies match pinned requirements.txt versions.'
  else
    fail 'Python dependency missing/mismatch or requirements not pinned; see full log.'
  fi
  if docker run --rm --pull=never --entrypoint node "$IMAGE" -e '
const fs=require("fs");
const parser=require("@babel/parser/package.json");
const lock=JSON.parse(fs.readFileSync("/app/package-lock.json","utf8"));
const wanted=lock.packages?.["node_modules/@babel/parser"]?.version;
console.log("Node",process.version,"Babel",parser.version,"expected",wanted);
if (!wanted || wanted!==parser.version) process.exit(2);
' 2>&1 | tee -a "$LOG"; then
    pass 'Node.js and Babel parser match package-lock.json.'
  else
    fail 'Node/Babel missing or version mismatch; see full log.'
  fi
  if docker run --rm --pull=never --shm-size=512m --user "$(id -u):$(id -g)" \
      -e HOME=/tmp --entrypoint python "$IMAGE" -c '
from playwright.sync_api import sync_playwright
import os
with sync_playwright() as p:
    path=p.chromium.executable_path
    assert os.path.isfile(path),"Browser executable missing"
    browser=p.chromium.launch(headless=True)
    print("Chromium launched:",browser.version)
    browser.close()
' >> "$LOG" 2>&1; then
    pass 'Chromium executable exists and browser headless launch succeeded under current UID.'
  else
    fail 'Chromium launch failed; check missing libraries, sandbox or browser files in full log.'
  fi
  if docker run --rm --pull=never "$IMAGE" --help >> "$LOG" 2>&1; then
    pass 'CLI --help executed.'
  else
    fail 'CLI startup failed; see full log.'
  fi
}
classify_build_failure() {
  log '[CHECK] Classifying Docker build failure from saved output...'
  if grep -Eqi 'Unable to connect to deb.debian.org|Failed to fetch http.*debian|Could not connect.*debian' "$LOG"; then
    fail 'APT_NETWORK: Debian package server unreachable during build. Check mirror/port/proxy; do not edit host apt without approval.'
  elif grep -Eqi 'Failed to install browsers|playwright.*download.*failed' "$LOG"; then
    fail 'PLAYWRIGHT_INSTALL: Browser installation failed. Inspect preceding dependency/download error.'
  elif grep -Eqi 'locked for [0-9]|snapshot.*does not exist' "$LOG"; then
    fail 'CONTAINERD_CONTENT: image-layer lock or snapshot anomaly. Do not delete containerd or restart Docker automatically.'
  elif grep -Eqi 'TLS handshake timeout|context deadline exceeded|connection refused|i/o timeout' "$LOG"; then
    fail 'NETWORK_TIMEOUT: network or registry request failed; verify endpoints and retry manually.'
  elif grep -Eqi 'no space left on device' "$LOG"; then
    fail 'DISK_FULL: insufficient space during image construction.'
  elif grep -Eqi 'permission denied|Cannot connect to the Docker daemon' "$LOG"; then
    fail 'PERMISSION_OR_DAEMON: Docker access issue; do not run sudo automatically.'
  else
    fail 'BUILD_FAILED_UNCLASSIFIED: inspect saved build log; no unproven root cause assigned.'
  fi
  log '[INFO] Relevant error lines (max 20):'
  grep -Ei 'error|failed|unable to connect|timeout|locked|no space left|permission denied' "$LOG" | tail -n 20 || true
}
run_build() {
  log "[CHECK] Docker build from existing Dockerfile: $IMAGE"
  if ! have_docker; then fail 'Docker inaccessible; build skipped.'; return; fi
  if command -v timeout >/dev/null 2>&1; then
    if timeout --signal=TERM --kill-after=15s 1800s docker build -t "$IMAGE" "$ROOT_DIR" >> "$LOG" 2>&1; then
      if have_image; then pass 'Docker BUILD_PASS: image exists.'
      else fail 'Docker returned success but image is missing.'; fi
    else
      classify_build_failure
    fi
  else
    warn 'timeout command missing; Docker build without external time cap.'
    if docker build -t "$IMAGE" "$ROOT_DIR" >> "$LOG" 2>&1; then
      if have_image; then pass 'Docker BUILD_PASS: image exists.'
      else fail 'Docker returned success but image is missing.'; fi
    else classify_build_failure; fi
  fi
  log "[INFO] Full build output stored in $LOG"
}
run_tests() {
  log '[CHECK] Existing unit tests in isolated container...'
  if ! have_docker || ! have_image; then
    fail 'Tests require existing Docker image; run build first.'; return
  fi
  if [[ ! -d "$ROOT_DIR/tests" ]]; then fail 'Project tests directory missing.'; return; fi
  if docker run --rm --pull=never -v "$ROOT_DIR/tests:/app/tests:ro" \
      --entrypoint python "$IMAGE" -m pytest -p no:cacheprovider -q tests >> "$LOG" 2>&1; then
    pass 'TEST_PASS: existing tests executed successfully.'
  else
    fail 'TEST_FAILED: pytest exited nonzero; inspect diagnostic log.'
  fi
}

log "[START] API Extractor diagnostics (mode=$MODE; image=$IMAGE)"
case "$MODE" in
  env) check_os; check_files ;;
  deps) check_os; check_files; check_deps ;;
  build) check_os; check_files; if (( FAIL == 0 )); then run_build; fi ;;
  test) check_os; check_files; if (( FAIL == 0 )); then run_tests; fi ;;
  check)
    check_os; check_files
    if (( FAIL == 0 )); then
      if (( DO_BUILD )); then run_build; fi
      if (( FAIL == 0 )); then check_deps; fi
      if (( DO_TEST && FAIL == 0 )); then run_tests; fi
    fi
    ;;
esac
report_finish
