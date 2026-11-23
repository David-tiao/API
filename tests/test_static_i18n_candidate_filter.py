"""Localization fetches are UI assets; only real API requests become candidates."""
from api_extractor.candidates import from_network_records
from api_extractor.normalization import normalize_candidates


def record(path, *, method="GET", resource_type="fetch"):
    return {
        "url": "https://shop.example.test" + path,
        "method": method,
        "http_method": method,
        "resource_type": resource_type,
        "status": 200,
        "request_index": 1,
        "response_content_type": "application/json",
    }


def test_known_static_i18n_json_is_not_an_api():
    urls = ["/assets/i18n/en.json", "/assets/i18n/en-US.json",
            "/assets/i18n/zh_CN.json", "/assets/i18n/en.json?v=12"]
    assert from_network_records([record(p) for p in urls]) == []


def test_api_json_and_unrelated_locale_paths_stay_visible():
    paths = ["/api/v1/users.json", "/api/locales/en.json",
             "/api/assets/i18n/en.json", "/assets/app/config.json",
             "/rest/products/search", "/socket.io/?EIO=4"]
    candidates = from_network_records([record(path) for path in paths])
    assert [candidate["url"].split("shop.example.test")[-1] for candidate in candidates] == paths


def test_static_path_post_and_websocket_are_not_silently_dropped():
    candidates = from_network_records([
        record("/assets/i18n/en.json", method="POST"),
        record("/assets/i18n/en.json", method="GET", resource_type="websocket"),
    ])
    assert len(candidates) == 2


def test_candidate_filter_does_not_modify_raw_network_evidence():
    input_records = [record("/assets/i18n/en.json"), record("/api/data.json")]
    before = [dict(row) for row in input_records]
    candidates = from_network_records(input_records)
    assert input_records == before
    assert len(candidates) == 1 and candidates[0]["url"].endswith("/api/data.json")
    assert normalize_candidates(candidates)[0]["path"] == "/api/data.json"
