from api_extractor.output import build_result, validate_result


def test_empty_result_matches_schema():
    result = build_result("test-site", [])
    validate_result(result)


def test_endpoint_result_matches_schema():
    result = build_result("test-site", [{
        "method": "GET", "path": "/api/users/{id}", "host": "api.example.com", "auth": "none",
        "params": {"path": [{"name": "id", "type": "string", "required": True}], "query": [], "body": []},
        "evidence": [{"type": "har", "file": "evidence/dynamic.har", "request_index": 0}],
        "confidence": 0.9, "note": "User resource endpoint",
    }])
    validate_result(result)
