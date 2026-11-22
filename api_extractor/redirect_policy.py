"""Small, fail-closed HTTP redirect decision table for intercepted browser requests.

This module only decides whether *the next network hop* may be made. The caller
must use Route.fetch(max_redirects=0) and reapply this decision at every hop.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

from .scope import ScopeGuard


@dataclass(frozen=True)
class RedirectStep:
    url: str
    method: str
    strip_request_body: bool
    strip_credentials: bool


def decide_redirect(
    current_url: str,
    status: int,
    location: str,
    current_method: str,
    guard: ScopeGuard,
) -> tuple[RedirectStep | None, str]:
    """Return (allowed hop, diagnostic reason), without making a request.

    Only POST -> GET on 301/302/303 is replayable as a safe *next* hop.
    POST itself was already sent as part of the page's legitimate workflow.
    Never replay non-idempotent POST/PUT/PATCH/DELETE on 307/308.
    """
    method = current_method.upper()
    if status not in {301, 302, 303, 307, 308} or not location:
        return None, "not_redirect"
    if any(c in location for c in "\r\n\x00"):
        return None, "malformed_location"
    try:
        next_url = urljoin(current_url, location)
        a, b = urlsplit(current_url), urlsplit(next_url)
        if not a.hostname or not b.hostname or not guard.is_allowed(next_url):
            return None, "blocked_by_scope"
        # Compare canonical IDNA hosts; do not let an explicit alternative port
        # receive a login continuation simply because its hostname matches.
        host_changed = (a.hostname.encode("idna").lower().rstrip(b".") !=
                        b.hostname.encode("idna").lower().rstrip(b"."))
        port_changed = ((a.port or (443 if a.scheme == "https" else 80)) !=
                        (b.port or (443 if b.scheme == "https" else 80)))
        scheme_changed = a.scheme.lower() != b.scheme.lower()
        if scheme_changed and not (a.scheme == "http" and b.scheme == "https" and not host_changed):
            return None, "unsafe_scheme_transition"
        if method == "POST" and status in {301, 302, 303}:
            # Authentication posts may redirect to a dashboard, but do not
            # forward them to a different host (even an allowlisted sibling).
            if host_changed or scheme_changed or port_changed:
                return None, "unsafe_post_transition"
            next_method = "GET"
        elif method in {"GET", "HEAD"}:
            next_method = "GET" if status == 303 and method != "HEAD" else method
        else:
            return None, "unsafe_method_transition"
        return RedirectStep(
            url=next_url,
            method=next_method,
            strip_request_body=(method == "POST" and next_method == "GET"),
            strip_credentials=(host_changed or scheme_changed or method != next_method),
        ), "allowed"
    except (ValueError, TypeError, UnicodeError):
        return None, "malformed_location"


def safe_followup_headers(headers: dict[str, str]) -> dict[str, str]:
    """Minimal headers for an origin/method-changing hop.

    A copied Authorization/Cookie or POST Content-Type/Length would misrepresent
    the new GET and could leak secrets. Playwright's request context manages
    origin-scoped cookies independently of this explicit header subset.
    """
    allowed = {"accept", "accept-language", "user-agent"}
    kept = {str(k): str(v) for k, v in headers.items()
            if str(k).lower() in allowed and isinstance(v, str)}
    return kept or {"Accept": "*/*"}
