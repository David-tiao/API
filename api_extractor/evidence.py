"""Evidence consistency checks before exporting API candidates.

Only paths under the configured output root may be referenced. HAR evidence
must actually identify the same request as its endpoint. No network calls.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

from .normalization import normalize_path


class EvidenceAuditor:
    def __init__(self, out_dir: Path):
        self.root = Path(out_dir).resolve()
        self._har_cache: dict[Path, list | None] = {}
        self._observed = self._load_log()

    @staticmethod
    def _identity(method: str, url: str) -> tuple[str, str, str] | None:
        parsed = urlsplit(url)
        if not parsed.hostname:
            return None
        return (method.upper(), parsed.hostname.lower(), normalize_path(parsed.path))

    def _load_log(self) -> set[tuple[str, str, str]]:
        """Index completed, actual dynamic requests; ignore zero-status placeholders."""
        index = set()
        path = self.root / "tool.log"
        if not path.is_file():
            return index
        with path.open(encoding="utf-8", errors="replace") as source:
            for line in source:
                try:
                    row = json.loads(line)
                    if row.get("phase") != "dynamic" or int(row.get("status", 0)) < 100:
                        continue
                    identity = self._identity(str(row.get("method", "")), str(row.get("url", "")))
                    if identity:
                        index.add(identity)
                except (ValueError, TypeError, AttributeError):
                    continue
        return index

    def _safe_file(self, filename: object) -> Path | None:
        if not isinstance(filename, str) or not filename:
            return None
        relative = Path(filename)
        if relative.is_absolute() or ".." in relative.parts:
            return None
        try:
            path = (self.root / relative).resolve(strict=True)
            if path.is_relative_to(self.root) and path.is_file() and path.stat().st_size > 0:
                return path
        except (OSError, ValueError):
            pass
        return None

    def _har_entries(self, path: Path) -> list | None:
        if path not in self._har_cache:
            try:
                if path.stat().st_size > 32 * 1024 * 1024:
                    raise ValueError("HAR file too large")
                data = json.loads(path.read_text(encoding="utf-8"))
                entries = data["log"]["entries"]
                if not isinstance(entries, list):
                    raise ValueError("HAR entries must be a list")
                self._har_cache[path] = entries
            except (OSError, ValueError, TypeError, KeyError):
                self._har_cache[path] = None
        return self._har_cache[path]

    def _valid_har(self, endpoint: dict, evidence: dict, path: Path) -> bool:
        idx = evidence.get("request_index")
        entries = self._har_entries(path)
        if not isinstance(idx, int) or isinstance(idx, bool) or entries is None or not (0 <= idx < len(entries)):
            return False
        entry = entries[idx]
        if not isinstance(entry, dict) or (entry.get("_requestIndex", idx) != idx):
            return False
        request = entry.get("request")
        if not isinstance(request, dict):
            return False
        method = str(request.get("method", "")).upper()
        identity = self._identity(method, str(request.get("url", "")))
        if identity is None or identity[1:] != (endpoint.get("host"), endpoint.get("path")):
            return False
        endpoint_method = endpoint.get("method")
        if endpoint_method == "WS":
            if method != "GET" or entry.get("_resourceType") != "websocket":
                return False
        elif endpoint_method == "GQL":
            if method not in {"GET", "POST"}:
                return False
        elif method != endpoint_method:
            return False
        return identity in self._observed

    def audit(self, endpoints: list[dict]) -> tuple[list[dict], int, int]:
        """Return (clean endpoints, invalid evidence count, dropped endpoint count)."""
        cleaned = []
        bad_refs = 0
        dropped = 0
        for endpoint in endpoints:
            valid = []
            for evidence in endpoint.get("evidence", []):
                if not isinstance(evidence, dict):
                    bad_refs += 1
                    continue
                path = self._safe_file(evidence.get("file"))
                kind = evidence.get("type")
                if path is None or kind not in {"bundle", "html", "har"}:
                    bad_refs += 1
                    continue
                if kind == "har" and not self._valid_har(endpoint, evidence, path):
                    bad_refs += 1
                    continue
                if kind in {"bundle", "html"}:
                    snippet = evidence.get("snippet")
                    if snippet and isinstance(snippet, str) and snippet not in path.read_text(encoding="utf-8", errors="replace"):
                        bad_refs += 1
                        continue
                valid.append(evidence)
            if valid:
                cleaned.append({**endpoint, "evidence": valid})
            else:
                dropped += 1
        return cleaned, bad_refs, dropped


def audit_endpoints(endpoints: list[dict], out_dir: Path) -> tuple[list[dict], int, int]:
    """Filter unresolvable/spurious evidence; only static files and real HAR requests pass."""
    return EvidenceAuditor(out_dir).audit(endpoints)
