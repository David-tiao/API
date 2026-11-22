from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from . import __version__


SCHEMA_PATH = Path(__file__).parent / "result.schema.json"


def build_result(site: str, endpoints: list[dict]) -> dict:
    return {
        "site": site,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "tool_version": __version__,
        "endpoints": endpoints,
    }


def validate_result(result: dict) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(result), key=lambda e: list(e.path))
    if errors:
        details = "; ".join(f"{list(e.path)}: {e.message}" for e in errors[:5])
        raise ValueError(f"result.json schema validation failed: {details}")


def write_result(path: str | Path, result: dict) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    validate_result(result)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(destination)

def write_static_review(path: str | Path, site: str, unverified: list[dict]) -> None:
    """Store source-code-only hints separately; do NOT fabricate request evidence.

    Deliberately omit source snippets, headers, query values and response bodies
    to avoid copying secrets into an extra diagnostic artifact.
    """
    rows = []
    for endpoint in unverified:
        sources = [
            {key: evidence[key] for key in ("type", "file", "loc") if key in evidence}
            for evidence in endpoint.get("evidence", [])
            if isinstance(evidence, dict) and evidence.get("type") in {"html", "bundle"}
        ]
        rows.append({
            "method": endpoint["method"],
            "host": endpoint["host"],
            "path": endpoint["path"],
            "reason": "no_observed_request",
            "sources": sources,
        })
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps({
            "site": site,
            "kind": "unverified_static_candidates",
            "candidates": rows,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(destination)
