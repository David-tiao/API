from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_SENSITIVE = ("token", "secret", "password", "passwd", "authorization", "api_key", "apikey", "signature", "sign", "session", "cookie", "code")


def redact_url(url: str) -> str:
    try:
        parts = urlsplit(url)
        pairs = []
        for key, value in parse_qsl(parts.query, keep_blank_values=True):
            if any(term in key.lower() for term in _SENSITIVE):
                value = "[REDACTED]"
            pairs.append((key, value))
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(pairs), ""))
    except Exception:
        return url


class JsonlLogger:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
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
