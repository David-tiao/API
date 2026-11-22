"""Scope regression tests for multilevel and private suffixes; all offline."""
import pytest
from api_extractor.scope import ScopeGuard, registrable_domain
import api_extractor.scope as scope


def test_co_za_unrelated_domain_is_blocked():
    guard = ScopeGuard('https://app.example.co.za/',
                       ['app.example.co.za', 'unrelated.co.za'])
    assert guard.is_allowed('https://app.example.co.za/api')
    assert not guard.is_allowed('https://unrelated.co.za/api')


def test_allow_authorized_sibling_subdomain():
    guard = ScopeGuard('https://app.example.co.za/',
                       ['app.example.co.za', 'api.example.co.za'])
    assert guard.is_allowed('https://api.example.co.za/api')


def test_private_public_suffix_is_not_shared_ownership():
    guard = ScopeGuard('https://foo.github.io/', ['foo.github.io', 'bar.github.io'])
    assert guard.is_allowed('https://foo.github.io/api')
    assert not guard.is_allowed('https://bar.github.io/api')


def test_unauthorized_subdomain_and_userinfo_denied():
    guard = ScopeGuard('https://app.example.com/', ['app.example.com'])
    assert not guard.is_allowed('https://api.example.com/users')
    assert not guard.is_allowed('https://attacker:password@app.example.com/users')
    with pytest.raises(ValueError):
        ScopeGuard('https://attacker:password@app.example.com/')


def test_ip_address_scope_is_exact():
    guard = ScopeGuard('http://127.0.0.1:3000/', ['127.0.0.1'])
    assert guard.is_allowed('ws://127.0.0.1:3000/socket')
    assert not guard.is_allowed('http://127.0.0.2:3000/')


def test_missing_psl_uses_exact_host_not_unsafe_suffix_guess(monkeypatch):
    monkeypatch.setattr(scope, '_psl', lambda: None)
    guard = ScopeGuard('https://app.example.co.za/',
                       ['app.example.co.za', 'api.example.co.za', 'unrelated.co.za'])
    assert guard.is_allowed('https://app.example.co.za/api')
    assert not guard.is_allowed('https://api.example.co.za/api')
    assert not guard.is_allowed('https://unrelated.co.za/api')


def test_unicode_domain_is_normalized():
    guard = ScopeGuard('https://bücher.example/', ['bücher.example'])
    assert guard.is_allowed('https://xn--bcher-kva.example/api')


def test_registrable_domain_has_full_suffix_table_or_conservative_fallback():
    assert registrable_domain('app.example.co.za') in ('example.co.za', 'app.example.co.za')
    assert registrable_domain('foo.github.io') == 'foo.github.io'
