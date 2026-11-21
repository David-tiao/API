from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit


_MULTI_LABEL_SUFFIXES = {
    "co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "net.au", "org.au",
    "co.nz", "org.nz", "co.jp", "ne.jp", "com.sg", "com.cn", "net.cn",
    "org.cn", "com.hk", "com.tw", "com.br", "com.mx", "co.in", "firm.in",
    "github.io", "pages.dev", "vercel.app", "netlify.app", "appspot.com", "cloudfront.net",
}


def _host(value: str) -> str:
    return (value or "").strip().lower().rstrip(".")


def registrable_domain(host: str) -> str:
    host = _host(host)
    if not host:
        return ""
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    suffix2 = ".".join(labels[-2:])
    if suffix2 in _MULTI_LABEL_SUFFIXES and len(labels) >= 3:
        return ".".join(labels[-3:])
    return suffix2


class ScopeGuard:
    """Allow only the target's registrable domain and configured allowed hosts."""

    def __init__(self, target: str, allowed_hosts: list[str] | None = None):
        parsed = urlsplit(target)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("--target must be an absolute http(s) URL")
        self.target_host = _host(parsed.hostname)
        self.target_domain = registrable_domain(self.target_host)
        self.allowed_hosts = [_host(x) for x in (allowed_hosts or []) if _host(x)]

    def is_allowed(self, url: str) -> bool:
        try:
            parsed = urlsplit(url)
            if parsed.scheme not in {"http", "https", "ws", "wss"} or not parsed.hostname:
                return False
            host = _host(parsed.hostname)
            if registrable_domain(host) != self.target_domain:
                return False
            if self.allowed_hosts:
                return any(host == allowed or host.endswith("." + allowed) for allowed in self.allowed_hosts)
            return True
        except (ValueError, TypeError):
            return False
