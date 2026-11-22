import json
from urllib.parse import parse_qs, urlsplit
from api_extractor.jsonl_logger import JsonlLogger, redact_url


def query_values(url):
    return parse_qs(urlsplit(url).query)


def test_redacts_credentials_and_secret_keys():
    source = 'https://alice:superSecret@app.example.com:8443/api/items?api_key=abc&code=otp123&key=hidden&jwt=jwt123&limit=2'
    sanitized = redact_url(source)
    assert 'alice' not in sanitized and 'superSecret' not in sanitized
    assert urlsplit(sanitized).netloc == 'app.example.com:8443'
    assert query_values(sanitized)['limit'] == ['2']
    for key in ('api_key','code','key','jwt'):
        assert query_values(sanitized)[key] == ['[REDACTED]']


def test_preserves_unrelated_business_field_names():
    sanitized = redact_url('https://example.com/api/items?design=blue&barcode=98765&token=secret')
    assert query_values(sanitized)['design'] == ['blue']
    assert query_values(sanitized)['barcode'] == ['98765']
    assert query_values(sanitized)['token'] == ['[REDACTED]']


def test_encoded_and_ipv6_userinfo():
    assert urlsplit(redact_url('https://u:p@[::1]:8080/a?csrfToken=s')).netloc == '[::1]:8080'
    assert query_values(redact_url('https://example.com/?access_token=a%2Bb'))['access_token'] == ['[REDACTED]']


def test_bad_port_and_url_do_not_leak_secret():
    assert redact_url('https://u:secret@site.test:badport/api') == '[REDACTED_URL]'


def test_jsonl_logger_never_writes_raw_userinfo_or_secret_params(tmp_path):
    p = tmp_path / 'tool.log'
    log = JsonlLogger(p)
    try:
        log.write('GET', 'https://u:p@app.example.com/?key=abc&offset=3', 200, 'dynamic', request_index=1)
    finally:
        log.close()
    body = p.read_text()
    assert 'key=abc' not in body and 'u:p@' not in body
    row = json.loads(body)
    assert row['status'] == 200 and row['request_index'] == 1
    assert query_values(row['url'])['key'] == ['[REDACTED]']
