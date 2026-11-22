"""Opt-in, explicitly authorized GET verification for local development only.

No paths are inferred or probed by default. This is intentionally NOT a
site-specific adaptation mechanism for the recruitment benchmark.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

import httpx

from .config import SiteConfig
from .jsonl_logger import JsonlLogger, redact_url
from .request_control import RequestGate
from .scope import ScopeGuard


class ExplicitGetVerifier:
    """Verify at most five exact, operator-authorized JSON GET URLs."""

    MAX_REQUESTS = 5

    def __init__(
        self,
        config: SiteConfig,
        guard: ScopeGuard,
        gate: RequestGate,
        logger: JsonlLogger,
        out_dir: Path,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = config
        self.guard = guard
        self.gate = gate
        self.logger = logger
        self.out_dir = Path(out_dir)
        self.transport = transport
        self.records: list[dict] = []
        self._entries: list[dict] = []

    @staticmethod
    def safe_exact_url(url: str) -> bool:
        """No query, fragment, placeholders, credentials or ambiguous path encoding."""
        try:
            value = urlsplit(url)
            if (value.scheme not in {"http", "https"} or not value.hostname
                    or value.username is not None or value.password is not None
                    or value.query or value.fragment or not value.path.startswith("/")):
                return False
            path = unquote(value.path)
            if ("\\" in path or "{" in path or "}" in path or
                    any(part in {".", ".."} for part in path.split("/"))):
                return False
            return True
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _json_response(content_type: str) -> bool:
        media_type = content_type.split(";", 1)[0].strip().lower()
        return media_type == "application/json" or media_type.endswith("+json")

    def _write_har(self) -> None:
        destination = self.out_dir / "evidence" / "probe.har"
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".har.tmp")
        temporary.write_text(json.dumps({
            "log": {"version": "1.2", "creator": {"name": "API Extractor", "version": "0.1.0"},
                    "entries": self._entries},
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(destination)

    async def run(self, candidates: list[dict]) -> list[dict]:
        self.records.clear()
        self._entries.clear()
        allowed = self.config.explicit_readonly_get_urls
        if not allowed:
            # An empty run also clears an old probe HAR in this output directory.
            self._write_har()
            return []

        declared = {
            row.get("url") for row in candidates
            if row.get("source") in {"ast", "regex", "html"}
            and str(row.get("method") or "").upper() == "GET"
        }
        urls = []
        for url in allowed:
            if (url in declared and url not in urls
                    and self.safe_exact_url(url) and self.guard.is_allowed(url)):
                urls.append(url)
            if len(urls) == self.MAX_REQUESTS:
                break
        if not urls:
            self._write_har()
            return []

        # No configured credentials or custom site headers: only neutral Accept/UA.
        # A real HTTP GET is sent only for an explicit exact URL in the allowlist.
        try:
            async with httpx.AsyncClient(
                transport=self.transport,
                follow_redirects=False,
                trust_env=self.transport is None,
                timeout=httpx.Timeout(8.0, connect=4.0),
                headers={"Accept": "application/json", "User-Agent": "API-Extractor/0.1.0"},
            ) as client:
                for url in urls:
                    try:
                        async with self.gate.slot():
                            async with client.stream("GET", url) as response:
                                status = response.status_code
                                media_type = response.headers.get("content-type", "")
                        index = len(self._entries)
                        # All actual attempts get a log line. Invalid/unexpected
                        # responses cannot count as proven endpoints.
                        self.logger.write("GET", url, status, "probe",
                                          request_index=index, resource_type="explicit_safe_get")
                        if not (200 <= status < 300 and self._json_response(media_type)):
                            continue
                        self._entries.append({
                            "request": {"method": "GET", "url": redact_url(url), "headers": []},
                            "response": {"status": status, "headers": [],
                                         "content": {"size": -1, "mimeType": media_type}},
                            "_requestIndex": index,
                            "_resourceType": "explicit_safe_get",
                        })
                        self.records.append({
                            "source": "verified_get", "url": url, "method": "GET",
                            "confidence": 0.95, "status": status,
                            "response_content_type": media_type,
                            "request_index": index,
                            "evidence_file": "evidence/probe.har",
                        })
                    except (httpx.HTTPError, ValueError) as exc:
                        self.logger.write("GET", url, 0, "probe", note=f"probe_error:{type(exc).__name__}")
        finally:
            # On budget cancellation, retain completed observations for the
            # pipeline's existing partial-results handling.
            self._write_har()
        return self.records
