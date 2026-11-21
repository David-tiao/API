from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from .crawler import ScriptRecord
from .scope import ScopeGuard


_ENDPOINT_LIKE = re.compile(r"(?:/api(?:/|$)|/graphql(?:/|$)|/rest(?:/|$)|/v\d+(?:/|$)|/(?:auth|login|logout|users?|orders?|products?|accounts?|sessions?)(?:/|$))", re.I)
_FETCH_CALL = re.compile(r"\bfetch\s*\(\s*[\"'`]([^\"'`]+)[\"'`](?:\s*,\s*\{[^}]{0,500}?\bmethod\s*:\s*[\"'`](GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)[\"'`])?", re.I | re.S)
_HTTP_CLIENT_CALL = re.compile(r"\b(?:axios|[A-Za-z_$][\w$]*)\.(get|post|put|patch|delete|head|options)\s*\(\s*[\"'`]([^\"'`]+)[\"'`]", re.I)
_XHR_OPEN_CALL = re.compile(r"\.open\s*\(\s*[\"'`](GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)[\"'`]\s*,\s*[\"'`]([^\"'`]+)[\"'`]", re.I)

_WS_CALL = re.compile(r"\bnew\s+WebSocket\s*\(\s*[\"'`]([^\"'`]+)[\"'`]", re.I)
_SSE_CALL = re.compile(r"\bnew\s+EventSource\s*\(\s*[\"'`]([^\"'`]+)[\"'`]", re.I)


class StaticAnalyzer:
    def __init__(self, project_root: Path, out_dir: Path, guard: ScopeGuard):
        self.project_root = project_root
        self.out_dir = out_dir
        self.guard = guard
        self.node_script = project_root / "tools" / "js_ast_analyzer.cjs"

    def analyze(self, script: ScriptRecord) -> tuple[list[dict], list[str]]:
        file_path = self.out_dir / script.local_file if script.local_file else None
        if not file_path or not file_path.exists():
            # Inline scripts are persisted by the crawler under the configured output directory.
            return self._regex_fallback(script)
        try:
            completed = subprocess.run(
                ["node", str(self.node_script), str(file_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=12,
            )
            if completed.returncode != 0 or not completed.stdout.strip():
                return self._regex_fallback(script)
            payload = json.loads(completed.stdout or "{}")
            records = payload.get("endpoints", [])
            chunks = payload.get("chunks", [])
            candidates = []
            lines = script.content.splitlines()
            for record in records:
                raw_url = str(record.get("url") or "").strip()
                if not raw_url:
                    continue
                resolved = self._resolve(raw_url, script.url)
                if not resolved or not self.guard.is_allowed(resolved):
                    continue
                path = urlsplit(resolved).path
                method = str(record.get("method") or "GET").upper()
                if not self._looks_like_api(path, method):
                    continue
                line = record.get("line")
                snippet = lines[int(line) - 1].strip()[:300] if line and 0 < int(line) <= len(lines) else ""
                candidates.append({
                    "method": method,
                    "url": resolved,
                    "source": "ast",
                    "confidence": 0.68,
                    "line": line,
                    "snippet": snippet,
                    "file": script.local_file,
                    "query_fields": record.get("query_fields") or [],
                    "body_fields": record.get("body_fields") or [],
                    "kind": record.get("kind"),
                })
            # Merge regex discoveries even if AST succeeded: WebSocket/EventSource
            # constructors and some wrappers are not AST-supported yet.
            fallback_candidates, fallback_chunks = self._regex_fallback(script)
            seen = {(row["method"], row["url"]) for row in candidates}
            for row in fallback_candidates:
                key = (row["method"], row["url"])
                if key not in seen:
                    candidates.append(row)
                    seen.add(key)
            chunks.extend(fallback_chunks)
            resolved_chunks = [self._resolve(x, script.url) for x in chunks]
            return candidates, [x for x in resolved_chunks if x and self.guard.is_allowed(x)]
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ValueError):
            return self._regex_fallback(script)

    @staticmethod
    def _resolve(raw_url: str, base_url: str) -> str | None:
        if raw_url.startswith(("http://", "https://")):
            return raw_url
        if raw_url and not raw_url.startswith(("data:", "blob:", "javascript:", "mailto:")):
            return urljoin(base_url, raw_url)
        return None

    @staticmethod
    def _looks_like_api(path: str, method: str) -> bool:
        if _ENDPOINT_LIKE.search(path):
            return True
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            return not path.lower().endswith((".js", ".css", ".png", ".jpg", ".svg", ".woff", ".ico"))
        return False

    def _regex_fallback(self, script: ScriptRecord) -> tuple[list[dict], list[str]]:
        candidates = []
        lines = script.content.splitlines()
        matches = []
        for pattern, method_group, url_group, default_method in (
            (_FETCH_CALL, 2, 1, "GET"),
            (_HTTP_CLIENT_CALL, 1, 2, "GET"),
            (_XHR_OPEN_CALL, 1, 2, "GET"),
        ):
            for match in pattern.finditer(script.content):
                method = (match.group(method_group) or default_method).upper()
                raw_url = match.group(url_group)
                matches.append((match.start(), method, raw_url, False))
        for pattern, method in ((_WS_CALL, "WS"), (_SSE_CALL, "GET")):
            for match in pattern.finditer(script.content):
                matches.append((match.start(), method, match.group(1), True))
        for position, method, raw_url, explicit_protocol in sorted(matches):
            resolved = self._resolve(raw_url, script.url)
            if not resolved or not self.guard.is_allowed(resolved):
                continue
            if not explicit_protocol and not self._looks_like_api(urlsplit(resolved).path, method):
                continue
            line = script.content.count("\n", 0, position) + 1
            snippet = lines[line - 1].strip()[:300] if line <= len(lines) else ""
            candidates.append({
                "method": method, "url": resolved, "source": "regex", "confidence": 0.52,
                "line": line, "snippet": snippet, "file": script.local_file,
                "query_fields": [], "body_fields": [], "kind": "network_call_regex",
            })
        chunks = re.findall(r"import\s*\(\s*[\"']([^\"']+\.m?js)[\"']\s*\)", script.content)
        return candidates, [urljoin(script.url, x) for x in chunks if self.guard.is_allowed(urljoin(script.url, x))]
