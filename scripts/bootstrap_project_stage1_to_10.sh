#!/usr/bin/env bash
# Project root: inferred from this script's location; no fixed /home/tao/API path.
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
cd "$ROOT_DIR"

BUILD_DOCKER=0
if [[ "${1:-}" == "--docker" ]]; then
  BUILD_DOCKER=1
elif [[ -n "${1:-}" ]]; then
  echo "Usage: $0 [--docker]" >&2
  exit 2
fi

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[ERROR] Required command not found: $1" >&2
    exit 1
  fi
}

require_command python3
require_command node
require_command npm

PYTHON_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
python3 - "$PYTHON_VERSION" <<'PY'
import sys
version = tuple(map(int, sys.argv[1].split(".")))
if version < (3, 11):
    raise SystemExit("Python 3.11 or newer is required.")
PY

if command -v git >/dev/null 2>&1 && [[ ! -d "$ROOT_DIR/.git" ]]; then
  echo "[INFO] Initializing Git repository..."
  git -C "$ROOT_DIR" init >/dev/null
fi

VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "[1/6] Creating Python virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "[ERROR] Failed to create virtual environment at $VENV_DIR" >&2
  exit 1
fi

echo "[2/6] Installing Python dependencies..."
"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install -r "$ROOT_DIR/requirements.txt"

echo "[3/6] Installing locked Node.js dependencies..."
npm --prefix "$ROOT_DIR" ci --no-audit --no-fund

echo "[4/6] Installing Playwright Chromium..."
"$PYTHON_BIN" -m playwright install chromium

echo "[5/6] Running tests and checking CLI..."
"$PYTHON_BIN" -m pytest "$ROOT_DIR/tests"
"$PYTHON_BIN" -m api_extractor.cli --help >/dev/null

if [[ "$BUILD_DOCKER" == "1" ]]; then
  require_command docker
  if ! docker info >/dev/null 2>&1; then
    echo "[ERROR] Docker is installed but the daemon is not running or accessible." >&2
    exit 1
  fi
  echo "[6/6] Building Docker image..."
  docker build -t api-extractor:0.1.0 "$ROOT_DIR"
else
  echo "[6/6] Docker build skipped. Run '$0 --docker' to build the image."
fi

cat <<EOF2

[OK] Project initialization completed.
Project root : $ROOT_DIR
Python       : $PYTHON_BIN
CLI check    : passed

Start command:
  bash "$ROOT_DIR/scripts/start_extractor_stage8.sh" \\
    "https://authorized-target.example/" \\
    "$ROOT_DIR/examples/site.example.json" \\
    "$ROOT_DIR/out/result.json" \\
    1200
EOF2
