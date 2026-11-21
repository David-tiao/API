from api_extractor.scope import ScopeGuard


def test_allows_target_and_configured_sibling_subdomain():
    guard = ScopeGuard("https://app.s3.lab/", ["app.s3.lab", "api.s3.lab", "static.s3.lab"])
    assert guard.is_allowed("https://app.s3.lab/api/users")
    assert guard.is_allowed("https://api.s3.lab/api/users")
    assert guard.is_allowed("https://static.s3.lab/assets/app.js")


def test_blocks_external_domain():
    guard = ScopeGuard("https://app.s3.lab/", ["app.s3.lab", "api.s3.lab"])
    assert not guard.is_allowed("https://evil.example/api/users")


def test_allowed_hosts_is_an_additional_restriction():
    guard = ScopeGuard("https://app.example.com/", ["app.example.com"])
    assert guard.is_allowed("https://app.example.com/api")
    assert not guard.is_allowed("https://api.example.com/api")


def test_ip_target_only_allows_same_ip():
    guard = ScopeGuard("http://127.0.0.1:8000/", ["127.0.0.1"])
    assert guard.is_allowed("http://127.0.0.1:8000/api")
    assert not guard.is_allowed("http://127.0.0.2:8000/api")


def test_private_suffix_tenants_are_not_treated_as_one_site():
    guard = ScopeGuard("https://tenant-a.github.io/", ["tenant-a.github.io"])
    assert guard.is_allowed("https://api.tenant-a.github.io/api")
    assert not guard.is_allowed("https://tenant-b.github.io/api")
