from api_extractor.normalization import infer_auth, normalize_candidates, normalize_path


def test_path_normalization():
    assert normalize_path("/api/users/123") == "/api/users/{id}"
    assert normalize_path("/api/orders/550e8400-e29b-41d4-a716-446655440000") == "/api/orders/{id}"


def test_candidate_merge_and_params():
    candidates = [{
        "method": "GET",
        "url": "https://api.example.com/api/users/123?page=2",
        "source": "dynamic",
        "confidence": 0.96,
        "request_index": 0,
        "headers": {"authorization": "Bearer [REDACTED]"},
        "response_content_type": "application/json",
        "response_fields": ["data", "data.id"],
    }]
    result = normalize_candidates(candidates)
    assert len(result) == 1
    assert result[0]["path"] == "/api/users/{id}"
    assert result[0]["auth"] == "bearer"
    assert result[0]["params"]["query"][0]["name"] == "page"
    assert result[0]["params"]["path"][0]["name"] == "id"
    assert result[0]["evidence"][0]["file"] == "evidence/dynamic.har"


def test_auth_classification():
    assert infer_auth({"authorization": "Bearer xxx"}, "https://x.test/api") == "bearer"
    assert infer_auth({"cookie": "sid=xxx"}, "https://x.test/api") == "cookie"
    assert infer_auth({"x-api-key": "xxx"}, "https://x.test/api") == "apikey"
    assert infer_auth({}, "https://x.test/api?signature=xxx") == "sign"


def test_graphql_endpoint_uses_gql_method():
    result = normalize_candidates([{
        "method": "POST",
        "url": "https://api.example.com/graphql",
        "source": "dynamic",
        "request_index": 1,
        "post_data": '{"query":"query GetUsers { users { id } }","variables":{}}',
    }])
    assert result[0]["method"] == "GQL"
