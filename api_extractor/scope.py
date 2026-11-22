"""Fail-closed URL scope validation using the system public suffix database.

libpsl's built-in suffix list includes multi-label ccTLD and private suffixes.
If it is unavailable, only exact host/descendants can be authorized; unrelated
sibling domains cannot be inferred safely without an authoritative suffix list.
"""
from __future__ import annotations

import ctypes
import ctypes.util
import ipaddress
from functools import lru_cache
from urllib.parse import urlsplit


def _host(value: str) -> str:
    name = (value or "").strip().lower().rstrip(".")
    try:
        return name.encode("idna").decode("ascii")
    except UnicodeError:
        return ""


@lru_cache(maxsize=1)
def _psl() -> tuple[ctypes.CDLL, int] | None:
    """Use the frozen public-suffix table shipped with the OS; never fetch it."""
    try:
        name = ctypes.util.find_library("psl")
        if not name:
            return None
        library = ctypes.CDLL(name)
        library.psl_builtin.argtypes = []
        library.psl_builtin.restype = ctypes.c_void_p
        library.psl_registrable_domain.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        library.psl_registrable_domain.restype = ctypes.c_char_p
        context = library.psl_builtin()
        if context:
            return (library, context)
    except (OSError, AttributeError, TypeError):
        pass
    return None


def registrable_domain(host: str) -> str:
    host = _host(host)
    if not host:
        return ""
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass
    psl = _psl()
    if psl is not None:
        library, context = psl
        try:
            domain = library.psl_registrable_domain(context, host.encode("ascii"))
            if domain:
                return domain.decode("ascii")
        except (UnicodeError, ValueError):
            pass
    # The absence of a PSL is not grounds for guessing that e.g. co.za is
    # a registrable domain. This fallback forbids sibling-domain access.
    return host


class ScopeGuard:
    """Allow only authorized hosts within the target's registrable domain."""

    def __init__(self, target: str, allowed_hosts: list[str] | None = None):
        parsed = urlsplit(target)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None):
            raise ValueError("--target must be an absolute http(s) URL without URL credentials")
        self.target_host = _host(parsed.hostname)
        if not self.target_host:
            raise ValueError("--target has an invalid hostname")
        self.target_domain = registrable_domain(self.target_host)
        self.allowed_hosts = [_host(x) for x in (allowed_hosts or []) if _host(x)]

    def is_allowed(self, url: str) -> bool:
        try:
            parsed = urlsplit(url)
            if (parsed.scheme not in {"http", "https", "ws", "wss"}
                    or not parsed.hostname or parsed.username is not None
                    or parsed.password is not None):
                return False
            host = _host(parsed.hostname)
            if not host or registrable_domain(host) != self.target_domain:
                return False
            if self.allowed_hosts:
                return any(host == allowed or host.endswith("." + allowed)
                           for allowed in self.allowed_hosts)
            return host == self.target_host or host.endswith("." + self.target_host)
        except (ValueError, TypeError):
            return False
