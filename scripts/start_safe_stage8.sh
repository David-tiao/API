#!/usr/bin/env bash
# API Extractor Stage 8: safe Docker job lifecycle (does not manage other containers).
set -Eeuo pipefail
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
OPS_DIR="$ROOT_DIR/out/operations"
IMAGE="${API_EXTRACTOR_IMAGE:-api-extractor:0.1.0}"
NETWORK="${API_EXTRACTOR_NETWORK:-bridge}"
IDENTITY="$(printf %s "$ROOT_DIR" | sha256sum | cut -c1-12)"
NAME="api-extractor-${UID:-$(id -u)}-${IDENTITY}"
LABEL="org.api-extractor.instance"
LOG_POINTER="$OPS_DIR/last_output_path"
LOG_OFFSET="$OPS_DIR/last_log_offset"

info() { printf '[INFO] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*" >&2; }
fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }
usage() {
  cat <<'HELP'
Usage (run from anywhere; relative config/out paths resolve under project root):
  bash scripts/start_safe_stage8.sh start <target-url> <site.json> [out/result.json] [budget=1200]
  bash scripts/start_safe_stage8.sh restart <target-url> <site.json> [out/result.json] [budget=1200]
  bash scripts/start_safe_stage8.sh stop
  bash scripts/start_safe_stage8.sh status
  bash scripts/start_safe_stage8.sh logs
  bash scripts/start_safe_stage8.sh doctor
  bash scripts/start_safe_stage8.sh build

Notes:
  A scan is a finite Docker job, NOT a permanently running server.
  'start' builds the image only if it is missing; 'build' explicitly rebuilds it.
  The script never restarts Docker or touches unrelated containers.
  Set API_EXTRACTOR_NETWORK=bench-net only if that network already exists.
HELP
}
ensure_project() {
  [[ -f "$ROOT_DIR/Dockerfile" && -f "$ROOT_DIR/api_extractor/cli.py" ]] || fail "Project files missing under $ROOT_DIR"
}
ensure_docker() {
  command -v docker >/dev/null 2>&1 || fail 'Docker executable not installed.'
  docker info >/dev/null 2>&1 || fail 'Docker daemon unavailable or current user lacks permission; run docker info for details.'
}
ensure_lock() {
  mkdir -p "$OPS_DIR"
  exec 9>"$OPS_DIR/lifecycle.lock"
  flock -n 9 || fail 'Another API Extractor lifecycle operation is in progress.'
}
exists() { docker container inspect "$NAME" >/dev/null 2>&1; }
owned() {
  local actual
  actual="$(docker inspect -f '{{index .Config.Labels "org.api-extractor.instance"}}' "$NAME" 2>/dev/null || true)"
  [[ "$actual" == "$IDENTITY" ]]
}
check_collision() {
  if exists && ! owned; then
    fail "Container name collision: $NAME is not owned by this project; refusing to touch it."
  fi
}
validate_result() {
  local result="$1" log="$2"
  [[ -s "$result" && -f "$log" ]] || { warn 'result.json or tool.log missing; job is not verified.'; return 1; }
  local offset=0 size=0
  if [[ -f "$LOG_OFFSET" ]]; then
    IFS= read -r offset < "$LOG_OFFSET" || offset=0
    [[ "$offset" =~ ^[0-9]+$ ]] || offset=0
  fi
  size="$(stat -c%s "$log" 2>/dev/null || echo 0)"
  if (( size <= offset )); then
    warn 'No new tool.log evidence written by this job; old results must not count as success.'
    return 1
  fi
  if tail -c "+$((offset+1))" "$log" | grep -Eq 'pipeline_error:|output_validation_error:'; then
    warn 'Current job log records a pipeline/output error; exit code 0 is NOT sufficient.'
    return 1
  fi
  python3 - "$result" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])
try:
    o=json.loads(p.read_text(encoding='utf-8'))
    assert isinstance(o,dict)
    assert all(k in o for k in ('site','generated_at','tool_version','endpoints'))
    assert isinstance(o['endpoints'],list)
    for ep in o['endpoints']:
        assert isinstance(ep,dict)
        assert all(k in ep for k in ('method','path','host','auth','params','evidence'))
        assert isinstance(ep['evidence'],list) and len(ep['evidence']) > 0
    print(f"[INFO] JSON basic checks passed; endpoints={len(o['endpoints'])}")
    if not o['endpoints']: print('[WARN] Zero endpoints; review tool.log and site accessibility.')
except Exception as e:
    print('[ERROR] Invalid output JSON:', type(e).__name__, file=sys.stderr)
    raise SystemExit(1)
PY
}
absolute_config() {
  local p="$1"
  [[ "$p" == /* ]] || p="$ROOT_DIR/$p"
  [[ -f "$p" && -r "$p" ]] || fail "Cannot read site config: $p"
  realpath -e -- "$p"
}
absolute_out() {
  local p="$1" dir
  [[ "$p" == /* ]] || p="$ROOT_DIR/$p"
  [[ "$p" == *.json ]] || fail 'Output filename must end with .json'
  dir="$(dirname -- "$p")"
  mkdir -p -- "$dir"
  [[ -w "$dir" ]] || fail "Output directory is not writable: $dir"
  printf '%s/%s\n' "$(realpath -e -- "$dir")" "$(basename -- "$p")"
}
validate_inputs() {
  local target="$1" config="$2" budget="$3"
  [[ "$budget" =~ ^[1-9][0-9]*$ ]] || fail 'Budget must be a positive integer of seconds.'
  command -v python3 >/dev/null 2>&1 || fail 'Python 3 (any modern version) required for JSON input/output checks; host Python 3.11+ is NOT required.'
  python3 - "$target" "$config" <<'PY'
import json,sys
from urllib.parse import urlsplit
try:
    u=urlsplit(sys.argv[1]); assert u.scheme in ('http','https') and u.hostname
    assert u.username is None and u.password is None, 'Do not embed credentials in target URL'
    obj=json.load(open(sys.argv[2],encoding='utf-8'))
    assert isinstance(obj,dict)
    a=obj.get('allowed_hosts',[])
    assert isinstance(a,list) and all(isinstance(x,str) for x in a)
    print('[INFO] Target URL and site.json basic checks passed (no network probe).')
except Exception as exc:
    print('[ERROR] Invalid target/config:',str(exc),file=sys.stderr)
    raise SystemExit(2)
PY
}
last_result() {
  [[ -f "$LOG_POINTER" ]] || return 1
  local p
  IFS= read -r p < "$LOG_POINTER" || true
  [[ -n "$p" ]] || return 1
  printf '%s\n' "$p"
}
stop_owned() {
  check_collision
  if ! exists; then info 'STOPPED: no managed container exists.'; return 0; fi
  local running
  running="$(docker inspect -f '{{.State.Running}}' "$NAME")"
  if [[ "$running" == true ]]; then
    info 'Stopping this project container with SIGTERM (10-second grace)...'
    docker stop --time 10 "$NAME" >/dev/null || fail 'Unable to stop managed container safely.'
  fi
  info 'STOPPED: managed container no longer running (no data deleted).'
}
cmd_status() {
  ensure_docker
  check_collision
  if ! exists; then info 'STOPPED: no managed container.'; return 0; fi
  local state exitcode
  state="$(docker inspect -f '{{.State.Status}}' "$NAME")"
  exitcode="$(docker inspect -f '{{.State.ExitCode}}' "$NAME")"
  if [[ "$state" == running ]]; then
    info "RUNNING: managed extraction job ($NAME)."
  elif [[ "$state" == exited && "$exitcode" == 0 ]]; then
    info 'COMPLETED: process exited with code 0; checking artifacts...'
    if p="$(last_result)"; then
      validate_result "$p" "$(dirname "$p")/tool.log" || fail 'Exit code 0 but extraction evidence is invalid.'
    else
      warn 'No previous result path recorded; cannot verify output.'
    fi
  else
    warn "FAILED or STOPPED: Docker state=$state exit_code=$exitcode; check logs."
    return 1
  fi
}
cmd_logs() {
  ensure_docker
  check_collision
  if exists; then
    info 'Docker logs (last 60 lines):'
    docker logs --tail 60 "$NAME" 2>&1 || true
  fi
  local p
  if p="$(last_result)" && [[ -f "$(dirname "$p")/tool.log" ]]; then
    info 'API request log (last 40 lines):'
    tail -n 40 "$(dirname "$p")/tool.log"
  else
    warn 'No previous tool.log found.'
  fi
}
cmd_build() {
  ensure_project; ensure_docker
  mkdir -p "$OPS_DIR"
  local build_log="$OPS_DIR/build_$(date +%Y%m%d_%H%M%S).log"
  info "Building $IMAGE from existing Dockerfile; full log: $build_log"
  if docker build -t "$IMAGE" "$ROOT_DIR" 2>&1 | tee "$build_log"; then
    docker image inspect "$IMAGE" >/dev/null || fail 'Build returned 0 but image is missing.'
    info 'BUILD_PASS: image present.'
  else
    fail "BUILD_FAILED: inspect $build_log. Try diagnose_environment_stage10.sh build for classification."
  fi
}
cmd_start() {
  local target="${1:-}" cfg_arg="${2:-}" out_arg="${3:-out/result.json}" budget="${4:-1200}"
  [[ -n "$target" && -n "$cfg_arg" ]] || { usage; exit 2; }
  ensure_project; ensure_docker
  command -v flock >/dev/null 2>&1 || fail 'flock required (util-linux).'
  local config out out_dir out_name
  config="$(absolute_config "$cfg_arg")"
  out="$(absolute_out "$out_arg")"
  out_dir="$(dirname -- "$out")"
  out_name="$(basename -- "$out")"
  validate_inputs "$target" "$config" "$budget"
  docker network inspect "$NETWORK" >/dev/null 2>&1 || fail "Docker network $NETWORK not found; select existing network (default: bridge)."
  # Do not change global Docker settings, apt configuration, or Docker service.
  if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    warn 'Image not present. One-time build will run; network/package errors may occur.'
    cmd_build
  fi
  ensure_lock
  check_collision
  if exists; then
    stop_owned
    info 'Removing only this project-owned previous container (results on host are kept).'
    docker rm "$NAME" >/dev/null || fail 'Could not remove previous managed container.'
  fi
  # Remember pre-run log length; the extractor appends log lines across runs.
  local old_size=0 env_args=() key
  if [[ -f "$out_dir/tool.log" ]]; then old_size="$(stat -c%s "$out_dir/tool.log")"; fi
  printf '%s\n' "$old_size" > "$LOG_OFFSET"
  for key in HTTP_PROXY HTTPS_PROXY NO_PROXY http_proxy https_proxy no_proxy; do
    if [[ -n "${!key:-}" ]]; then env_args+=(-e "$key"); fi
  done
  # Do not pass credentials through shell output; site.json is mounted read-only.
  local cid
  cid="$(docker create \
    --name "$NAME" \
    --label "${LABEL}=$IDENTITY" \
    --network "$NETWORK" \
    --user "$(id -u):$(id -g)" \
    --env HOME=/tmp \
    --shm-size=512m \
    "${env_args[@]}" \
    -v "$config:/cfg/site.json:ro" \
    -v "$out_dir:/out" \
    "$IMAGE" --target "$target" --config /cfg/site.json \
    --out "/out/$out_name" --budget "$budget")" || fail 'Docker container creation failed.'
  printf '%s\n' "$out" > "$LOG_POINTER"
  flock -u 9
  info "Starting managed job in foreground ($NAME), budget ${budget}s."
  interrupted() {
    warn 'Interrupted. Stopping only the verified managed API Extractor container...'
    if exists && owned; then docker stop --time 10 "$NAME" >/dev/null 2>&1 || true; fi
    exit 130
  }
  trap interrupted INT TERM
  local start_status exitcode state
  start_status=0
  if command -v timeout >/dev/null 2>&1; then
    timeout --signal=TERM --kill-after=10s "${budget}s" docker start --attach "$cid" || start_status=$?
  else
    docker start --attach "$cid" || start_status=$?
  fi
  if [[ "$start_status" == 124 ]]; then
    warn 'Runtime exceeded budget. Stopping only this managed container.'
    if exists && owned; then docker stop --time 10 "$NAME" >/dev/null 2>&1 || true; fi
    fail 'SCAN_TIMEOUT: extraction did not exit in the configured time budget.'
  fi
  trap - INT TERM
  state="$(docker inspect -f '{{.State.Status}}' "$NAME" 2>/dev/null || true)"
  exitcode="$(docker inspect -f '{{.State.ExitCode}}' "$NAME" 2>/dev/null || true)"
  if [[ "$state" != exited ]]; then
    fail "Job ended in unexpected state=$state (Docker client exit=$start_status). Check status/logs."
  fi
  [[ "$exitcode" == 0 ]] || fail "Extraction process exited with code $exitcode. Use 'logs' or diagnose script."
  validate_result "$out" "$out_dir/tool.log" || fail 'Process exited 0 but output validation or pipeline-log checks failed.'
  info "COMPLETED: result=$out; tool log=$out_dir/tool.log"
}

command="${1:-help}"
shift || true
case "$command" in
  help|-h|--help) usage ;;
  start) cmd_start "$@" ;;
  restart) cmd_start "$@" ;;
  stop) ensure_docker; ensure_lock; stop_owned ;;
  status) cmd_status ;;
  logs) cmd_logs ;;
  doctor)
    [[ -f "$SCRIPT_DIR/diagnose_environment_stage10.sh" ]] || fail 'Diagnostic script not installed.'
    bash "$SCRIPT_DIR/diagnose_environment_stage10.sh" env ;;
  build) cmd_build ;;
  *) usage; exit 2 ;;
esac
