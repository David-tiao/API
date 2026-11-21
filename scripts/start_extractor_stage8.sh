#!/usr/bin/env bash
# One-command launcher for the Stage 8 CLI contract.
# Project root is inferred from this script, so the project can live at /home/tao/API
# or any other directory without editing this file.
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
CALLER_DIR="$(pwd -P)"

TARGET="${1:-}"
CONFIG_ARG="${2:-}"
OUT_ARG="${3:-}"
BUDGET="${4:-1200}"

usage() {
  cat >&2 <<EOF2
Usage:
  $0 <target-url> <site.json> <output-result.json> [budget-seconds]

Example (run from /home/tao/API):
  bash scripts/start_extractor_stage8.sh \\
    "https://authorized-target.example/" \\
    "./examples/site.example.json" \\
    "./out/result.json" \\
    1200

Environment:
  API_EXTRACTOR_MODE=auto|docker|local   Default: auto
  API_EXTRACTOR_IMAGE                   Default: api-extractor:0.1.0
  API_EXTRACTOR_NETWORK                 Default: bench-net
EOF2
}

if [[ -z "$TARGET" || -z "$CONFIG_ARG" || -z "$OUT_ARG" ]]; then
  usage
  exit 2
fi

if [[ ! "$BUDGET" =~ ^[1-9][0-9]*$ ]]; then
  echo "[ERROR] budget must be a positive integer (seconds)." >&2
  exit 2
fi

# Resolve relative input/output paths against the directory from which the user
# invoked the command, not against the script directory.
resolve_existing_file() {
  local input="$1"
  local candidate
  if [[ "$input" = /* ]]; then
    candidate="$input"
  else
    candidate="$CALLER_DIR/$input"
  fi
  if [[ ! -f "$candidate" ]]; then
    echo "[ERROR] File not found: $candidate" >&2
    exit 2
  fi
  (cd "$(dirname "$candidate")" && printf '%s/%s\n' "$(pwd -P)" "$(basename "$candidate")")
}

resolve_output_file() {
  local input="$1"
  local candidate dir name
  if [[ "$input" = /* ]]; then
    candidate="$input"
  else
    candidate="$CALLER_DIR/$input"
  fi
  dir="$(dirname "$candidate")"
  name="$(basename "$candidate")"
  mkdir -p "$dir"
  dir="$(cd "$dir" && pwd -P)"
  printf '%s/%s\n' "$dir" "$name"
}

CONFIG="$(resolve_existing_file "$CONFIG_ARG")"
OUT_FILE="$(resolve_output_file "$OUT_ARG")"
OUT_DIR="$(dirname "$OUT_FILE")"
OUT_NAME="$(basename "$OUT_FILE")"
LOG_FILE="$OUT_DIR/tool.log"

IMAGE="${API_EXTRACTOR_IMAGE:-api-extractor:0.1.0}"
NETWORK="${API_EXTRACTOR_NETWORK:-bench-net}"
MODE="${API_EXTRACTOR_MODE:-auto}"

is_docker_ready() {
  command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1
}

if [[ "$MODE" == "auto" ]]; then
  if is_docker_ready; then
    MODE="docker"
  else
    MODE="local"
  fi
fi

case "$MODE" in
  docker)
    if ! is_docker_ready; then
      echo "[ERROR] Docker mode requested, but Docker is unavailable or its daemon is not running." >&2
      echo "        Start Docker, or set API_EXTRACTOR_MODE=local." >&2
      exit 1
    fi

    echo "[1/3] Building image: $IMAGE"
    docker build -t "$IMAGE" "$ROOT_DIR"

    if ! docker network inspect "$NETWORK" >/dev/null 2>&1; then
      echo "[2/3] Creating Docker network: $NETWORK"
      docker network create --driver bridge "$NETWORK" >/dev/null
    else
      echo "[2/3] Reusing Docker network: $NETWORK"
    fi

    DOCKER_ENV_ARGS=()
    if [[ -n "${HTTP_PROXY:-}" ]]; then DOCKER_ENV_ARGS+=(-e "HTTP_PROXY=$HTTP_PROXY"); fi
    if [[ -n "${HTTPS_PROXY:-}" ]]; then DOCKER_ENV_ARGS+=(-e "HTTPS_PROXY=$HTTPS_PROXY"); fi
    if [[ -n "${http_proxy:-}" ]]; then DOCKER_ENV_ARGS+=(-e "http_proxy=$http_proxy"); fi
    if [[ -n "${https_proxy:-}" ]]; then DOCKER_ENV_ARGS+=(-e "https_proxy=$https_proxy"); fi

    echo "[3/3] Running API Extractor in Docker..."
    docker run --rm \
      --network "$NETWORK" \
      -v "$CONFIG:/cfg/site.json:ro" \
      -v "$OUT_DIR:/out" \
      "${DOCKER_ENV_ARGS[@]}" \
      "$IMAGE" \
      --target "$TARGET" \
      --config /cfg/site.json \
      --out "/out/$OUT_NAME" \
      --budget "$BUDGET"
    ;;

  local)
    PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
    if [[ ! -x "$PYTHON_BIN" ]]; then
      echo "[INFO] Local environment not found; running the bootstrap script..."
      bash "$ROOT_DIR/scripts/bootstrap_project_stage1_to_10.sh"
    fi
    if [[ ! -x "$PYTHON_BIN" ]]; then
      echo "[ERROR] Python environment is still unavailable: $PYTHON_BIN" >&2
      exit 1
    fi

    echo "[INFO] Running API Extractor locally..."
    cd "$ROOT_DIR"
    "$PYTHON_BIN" -m api_extractor.cli \
      --target "$TARGET" \
      --config "$CONFIG" \
      --out "$OUT_FILE" \
      --budget "$BUDGET"
    ;;

  *)
    echo "[ERROR] Invalid API_EXTRACTOR_MODE: $MODE (expected auto, docker or local)." >&2
    exit 2
    ;;
esac

if [[ ! -s "$OUT_FILE" ]]; then
  echo "[ERROR] The extractor did not create a non-empty result file: $OUT_FILE" >&2
  exit 1
fi
if [[ ! -f "$LOG_FILE" ]]; then
  echo "[ERROR] tool.log was not created: $LOG_FILE" >&2
  exit 1
fi

echo "[OK] Extraction completed."
echo "Result : $OUT_FILE"
echo "Log    : $LOG_FILE"
echo "Evidence directory (if generated): $OUT_DIR/evidence"
