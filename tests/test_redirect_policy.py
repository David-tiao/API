"""Pure redirect policy tests for auth and upgrade safety decisions."""
import pytest
from api_extractor.redirect_policy import decide_redirect
from api_extractor.scope import ScopeGuard

BASE = 'http://app.example.com/'
GUARD = ScopeGuard(BASE, ['app.example.com', 'api.example.com'])

@pytest.mark.parametrize('status', [301, 302, 303])
def test_post_auth_redirect_switches_to_same_host_get(status):
    step, reason = decide_redirect(BASE+'api/login', status, '/dashboard', 'POST', GUARD)
    assert reason == 'allowed'
    assert step.url == BASE+'dashboard'
    assert step.method == 'GET' and step.strip_request_body and step.strip_credentials

@pytest.mark.parametrize('status', [307, 308])
def test_post_body_is_never_replayed_on_redirect(status):
    step, reason = decide_redirect(BASE+'api/login', status, '/dashboard', 'POST', GUARD)
    assert step is None and reason == 'unsafe_method_transition'

@pytest.mark.parametrize('next_url', ['http://api.example.com/dash', 'http://bad.example.com/dash', 'https://app.example.com/dash'])
def test_post_cannot_be_replayed_or_carried_to_different_origin(next_url):
    step, _ = decide_redirect(BASE+'api/login', 303, next_url, 'POST', GUARD)
    assert step is None


def test_safe_get_same_host_https_upgrade():
    step, reason = decide_redirect(BASE+'dashboard', 302, 'https://app.example.com/dashboard', 'GET', GUARD)
    assert reason == 'allowed'
    assert step.method == 'GET' and step.strip_credentials


def test_https_to_http_downgrade_forbidden():
    guard = ScopeGuard('https://app.example.com/', ['app.example.com'])
    step, reason = decide_redirect('https://app.example.com/login', 302, 'http://app.example.com/', 'GET', guard)
    assert step is None and reason == 'unsafe_scheme_transition'


def test_authorized_get_sibling_is_scrubbed():
    step, reason = decide_redirect(BASE+'view', 302, 'http://api.example.com/items', 'GET', GUARD)
    assert reason == 'allowed' and step.strip_credentials


def test_external_redirect_is_blocked():
    step, reason = decide_redirect(BASE+'view', 302, 'http://offscope.example.net/items', 'GET', GUARD)
    assert step is None and reason == 'blocked_by_scope'


def test_username_password_in_redirect_are_blocked():
    step, reason = decide_redirect(BASE+'view', 302, 'http://alice:pw@app.example.com/items', 'GET', GUARD)
    assert step is None and reason == 'blocked_by_scope'

@pytest.mark.parametrize('method', ['PUT', 'PATCH', 'DELETE'])
def test_unknown_state_change_redirect_cannot_be_replayed(method):
    step, reason = decide_redirect(BASE+'api/item', 303, '/dashboard', method, GUARD)
    assert step is None and reason == 'unsafe_method_transition'

@pytest.mark.parametrize('loc', ['https://app.example.com/\r\nX: injected', 'javascript:alert(1)', 'ftp://app.example.com/a', 'http://evil.test/a'])
def test_invalid_or_unsafe_destination_fails_closed(loc):
    step, _ = decide_redirect(BASE+'view', 302, loc, 'GET', GUARD)
    assert step is None


def test_relative_same_host_get_remains_unmodified():
    step, reason = decide_redirect(BASE+'redir', 307, '/ok', 'GET', GUARD)
    assert reason=='allowed' and step.method == 'GET' and not step.strip_credentials


def test_post_redirect_to_different_port_denied():
    step, reason = decide_redirect('http://app.example.com:8765/api/session', 303,
                                   'http://app.example.com:8766/dashboard', 'POST', GUARD)
    assert step is None and reason == 'unsafe_post_transition'


def test_followup_headers_remove_post_body_and_credentials():
    from api_extractor.redirect_policy import safe_followup_headers
    cleaned = safe_followup_headers({
        'Accept': 'text/html', 'Cookie': 'session=top-secret',
        'Authorization': 'Bearer token', 'Content-Type': 'application/x-www-form-urlencoded',
        'Content-Length': '123', 'x-api-key': 'api-secret', 'User-Agent': 'Browser',
    })
    assert cleaned == {'Accept': 'text/html', 'User-Agent': 'Browser'}


def test_followup_headers_without_safe_keys_use_nonempty_default():
    from api_extractor.redirect_policy import safe_followup_headers
    assert safe_followup_headers({'Cookie':'secret'}) == {'Accept':'*/*'}
