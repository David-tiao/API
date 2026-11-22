"""Safe signature metadata uses field names only, not secret values."""
import json

from api_extractor.signature_semantics import observed_signature_fields
from api_extractor.normalization import normalize_candidates


def test_header_query_and_nested_body_signature_fields():
    rows = observed_signature_fields(
        {"X-Signature": "secret-header", "Cookie": "test"},
        "https://app.example.com/api/items?sig=secret-query&page=2",
        json.dumps({"security": {"signature": "secret-body"}}),
    )
    assert rows == ["body:security.signature", "header:x-signature", "query:sig"]
    assert not any("secret-" in row for row in rows)


def test_urlencoded_body_signing_and_case_dedup():
    assert observed_signature_fields(
        {"X-Signature": "a", "x-signature": "b"},
        "https://app.example.com/?SIG=a&sig=b",
        "name=hello&sign=confidential",
    ) == ["body:sign", "header:x-signature", "query:sig"]


def test_unrelated_design_and_signup_are_not_signatures():
    assert observed_signature_fields(
        {"X-Design": "new"},
        "https://app.example.com/?design=page&signup=1",
        '{"signature_hint":"not a signature"}',
    ) == []


def test_invalid_names_and_large_request_body_are_rejected():
    assert observed_signature_fields({}, "https://app.example.com/", '{"bad\\nsignature":"x","signature":"y"}') == [
        "body:signature"
    ]
    large = "{" + '"payload":"' + "x" * (128 * 1024) + '"}'
    assert observed_signature_fields({}, "https://app.example.com/", large) == []


def test_nested_array_field_names_are_extracted():
    assert observed_signature_fields({}, "https://app.example.com/", '[{"signature":"a"},{"hmac":"b"}]') == [
        "body:hmac", "body:signature"
    ]


def sample(signed=False, status=200):
    return {
        "source": "dynamic", "method": "GET", "status": status,
        "url": ("https://app.example.com/api/report?sig=private" if signed
                else "https://app.example.com/api/report?page=2"),
        "headers": ({"X-Signature": "another-private"} if signed else {"Cookie": "session"}),
        "request_index": (0 if signed else 1),
    }


def test_merge_preserves_sign_auth_in_any_candidate_order():
    for candidates in (
        [sample(signed=True), sample()],
        [sample(), sample(signed=True)],
    ):
        result = normalize_candidates(candidates)
        assert len(result) == 1
        endpoint = result[0]
        assert endpoint["auth"] == "sign"
        assert "header:x-signature" in endpoint["note"]
        assert "query:sig" in endpoint["note"]
        assert "algorithm not reconstructed" in endpoint["note"]
        assert "private" not in endpoint["note"]
        assert len(endpoint["evidence"]) == 2


def test_failed_network_response_does_not_claim_signature():
    result = normalize_candidates([sample(signed=True, status=500), sample()])
    assert len(result) == 1
    assert result[0]["auth"] == "cookie"
    assert "Signing fields observed" not in result[0]["note"]


def test_nested_signing_json_body_keeps_raw_values_out_of_notes():
    rows = normalize_candidates([{
        "source": "dynamic", "method": "POST", "status": 200,
        "url": "https://app.example.com/api/signed",
        "headers": {}, "post_data": '{"security":{"signature":"secret-raw"}}',
        "request_index": 1,
    }])
    assert len(rows) == 1 and rows[0]["auth"] == "sign"
    assert "body:security.signature" in rows[0]["note"]
    assert "secret-raw" not in rows[0]["note"]
