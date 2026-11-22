from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Short names are matched as whole keys; long, unambiguous words can appear
# inside compound query names. Avoid treating "design" or "barcode" as secrets.
_SENSITIVE_NAMES = {
    "auth", "code", "jwt", "key", "otp", "sid", "sign", "sig",
    "token", "secret", "password", "passwd", "authorization", "apikey",
    "signature", "session", "cookie", "csrf", "xsrf", "otpcode",
}
_SENSITIVE_PARTS = (
    "token", "secret", "password", "passwd", "authorization", "apikey",
    "signature", "session", "cookie", "csrf", "xsrf",
)


def _sensitive_query_key(name: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", name.lower())
    if normalized in _SENSITIVE_NAMES or any(part in normalized for part in _SENSITIVE_PARTS):
        return True
    words = re.findall(r"[a-z0-9]+", name.lower())
    return any(word in {"auth", "code", "key", "otp", "sid", "sign", "sig", "jwt"} for word in words)


def redact_url(url: str) -> str:
    """Remove URL credentials and sensitive query values without changing request path."""
    try:
        parts = urlsplit(url)
        netloc = parts.netloc
        if parts.username is not None or parts.password is not None:
            host = parts.hostname
            if not host:
                return "[REDACTED_URL]"
            netloc = f"[{host}]" if ":" in host else host
            if parts.port is not None:
                netloc = f"{netloc}:{parts.port}"
        pairs = [(key, "[REDACTED]" if _sensitive_query_key(key) else value)
                 for key, value in parse_qsl(parts.query, keep_blank_values=True)]
        return urlunsplit((parts.scheme, netloc, parts.path, urlencode(pairs), ""))
    except (TypeError, ValueError):
        # Do not return malformed URLs which might contain raw credentials.
        return "[REDACTED_URL]"


class JsonlLogger:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # tool.log is append-only. Remember this run's byte boundary so evidence
        # cannot be incorrectly confirmed by a prior scan's request records.
        self.start_offset = self.path.stat().st_size if self.path.exists() else 0
        self._file = self.path.open("a", encoding="utf-8")
        self._lock = threading.Lock()

    def write(self, method: str, url: str, status: int, phase: str, **extra: object) -> None:
        row = {
            "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds"),
            "method": method,
            "url": redact_url(url),
            "status": int(status),
            "phase": phase,
        }
        row.update({k: v for k, v in extra.items() if v is not None})
        with self._lock:
            self._file.write(json.dumps(row, ensure_ascii=False) + "\n")
            self._file.flush()

    def close(self) -> None:
        with self._lock:
            if not self._file.closed:
                self._file.close()
