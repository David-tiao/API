from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class SiteConfig:
    site_id: str
    entry: str | None
    allowed_hosts: list[str]
    credentials: list[dict[str, Any]]
    headers: dict[str, str]
    notes: str = ""


def load_site_config(path: str | Path) -> SiteConfig:
    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("site config must be a JSON object")

    allowed_hosts = data.get("allowed_hosts") or []
    credentials = data.get("credentials") or []
    headers = data.get("headers") or {}
    if not isinstance(allowed_hosts, list) or not all(isinstance(x, str) for x in allowed_hosts):
        raise ValueError("allowed_hosts must be an array of host strings")
    if not isinstance(credentials, list) or not all(isinstance(x, dict) for x in credentials):
        raise ValueError("credentials must be an array of objects")
    if not isinstance(headers, dict):
        raise ValueError("headers must be a JSON object")

    return SiteConfig(
        site_id=str(data.get("site_id") or "unknown"),
        entry=data.get("entry"),
        allowed_hosts=[h.strip().lower().rstrip(".") for h in allowed_hosts if h.strip()],
        credentials=credentials,
        headers={str(k): str(v) for k, v in headers.items()},
        notes=str(data.get("notes") or ""),
    )
