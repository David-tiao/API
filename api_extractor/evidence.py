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
    def __init__(self, out_dir: Path, log_start_offset: int = 0):
        self.root = Path(out_dir).resolve()
        self.log_start_offset = max(0, log_start_offset)
        self._har_cache: dict[Path, list | None] = {}
        self._observed = self._load_log()

    @staticmethod
    def _identity(method: str, url: str) -> tuple[str, str, str] | None:
        parsed = urlsplit(url)
        if not parsed.hostname:
            return None
        return (method.upper(), parsed.hostname.lower(), normalize_path(parsed.path))

    def _load_log(self) -> set[tuple[str, str, str, int, int]]:
        """Index valid dynamic requests from this invocation's JSONL rows only."""
        index = set()
        path = self.root / "tool.log"
        if not path.is_file():
            return index
        with path.open("rb") as source:
            source.seek(self.log_start_offset)
            for raw in source:
                try:
                    row = json.loads(raw)
                    if row.get("phase") != "dynamic":
                        continue
                    status = int(row.get("status", 0))
                    idx = row.get("request_index")
                    if not isinstance(idx, int) or isinstance(idx, bool):
                        continue
                    if status < 100 or (status >= 400 and status not in {401, 403}):
                        continue
                    identity = self._identity(str(row.get("method", "")), str(row.get("url", "")))
                    if identity:
                        index.add((*identity, idx, status))
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
        response = entry.get("response")
        if not isinstance(request, dict) or not isinstance(response, dict):
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
        try:
            status = int(response.get("status", 0))
        except (TypeError, ValueError):
            return False
        return (*identity, idx, status) in self._observed

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


def audit_endpoints(
    endpoints: list[dict], out_dir: Path, log_start_offset: int = 0
) -> tuple[list[dict], int, int]:
    """Keep evidence backed by source files or this run's observed requests."""
    return EvidenceAuditor(out_dir, log_start_offset).audit(endpoints)

def split_by_request_proof(endpoints: list[dict]) -> tuple[list[dict], list[dict]]:
    """Partition *already audited* endpoints by real HTTP/WS request evidence.

    JS/HTML excerpts prove declarations, not that the browser requested an API.
    Call only after EvidenceAuditor validated HAR against the current run log.
    """
    confirmed, static_only = [], []
    for endpoint in endpoints:
        if any(isinstance(ev, dict) and ev.get("type") == "har"
               for ev in endpoint.get("evidence", [])):
            confirmed.append(endpoint)
        else:
            static_only.append(endpoint)
    return confirmed, static_only
