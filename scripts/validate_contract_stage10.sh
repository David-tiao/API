#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-}"
CONFIG="${2:-}"
OUT_FILE="${3:-$ROOT_DIR/out/result.json}"
BUDGET="${4:-1200}"

if [[ -z "$TARGET" || -z "$CONFIG" ]]; then
  echo "Usage: $0 <target-url> <site.json> [out/result.json] [budget-seconds]" >&2
  exit 2
fi

"$ROOT_DIR/scripts/start_extractor_stage8.sh" "$TARGET" "$CONFIG" "$OUT_FILE" "$BUDGET"

VALIDATOR="$ROOT_DIR/.venv/bin/python"
if [[ ! -x "$VALIDATOR" ]]; then
  if command -v python3 >/dev/null 2>&1 && python3 -c 'import jsonschema' >/dev/null 2>&1; then
    VALIDATOR="$(command -v python3)"
  elif command -v docker >/dev/null 2>&1 && docker image inspect api-extractor:0.1.0 >/dev/null 2>&1; then
    OUT_DIR="$(cd "$(dirname "$OUT_FILE")" && pwd)"
    OUT_NAME="$(basename "$OUT_FILE")"
    docker run --rm -v "$OUT_DIR:/out:ro" --entrypoint python api-extractor:0.1.0 -c \
      'import json,sys; from pathlib import Path; from jsonschema import Draft202012Validator; r=json.loads(Path("/out/"+sys.argv[1]).read_text()); s=json.loads(Path("/app/api_extractor/result.schema.json").read_text()); e=list(Draft202012Validator(s).iter_errors(r)); print("Contract check passed:",len(r["endpoints"]),"endpoint(s)") if not e else sys.exit("Schema validation failed: "+"; ".join(x.message for x in e[:5]))' \
      "$OUT_NAME"
    exit $?
  else
    echo "[ERROR] No Python environment with jsonschema found. Run bootstrap first." >&2
    exit 1
  fi
fi

"$VALIDATOR" - "$OUT_FILE" "$(dirname "$OUT_FILE")/tool.log" "$ROOT_DIR/api_extractor/result.schema.json" <<'PY'
import json, pathlib, sys
from jsonschema import Draft202012Validator
result_path = pathlib.Path(sys.argv[1])
log_path = pathlib.Path(sys.argv[2])
schema_path = pathlib.Path(sys.argv[3])
result = json.loads(result_path.read_text(encoding="utf-8"))
schema = json.loads(schema_path.read_text(encoding="utf-8"))
errors = list(Draft202012Validator(schema).iter_errors(result))
if errors:
    raise SystemExit("Schema validation failed: " + "; ".join(e.message for e in errors[:5]))
if not log_path.exists():
    raise SystemExit("tool.log missing")
print(f"Contract check passed: {len(result['endpoints'])} endpoint(s)")
PY
