"""Offline GraphQL recognition and secret-free output regression tests."""
import json
from urllib.parse import urlencode

import pytest

from api_extractor.candidates import from_network_records
from api_extractor.graphql_semantics import (
    is_graphql_request, operation_note, observed_variable_types,
)
from api_extractor.normalization import normalize_candidates

BASE = "https://app.example.com"


def candidate(path, data=None, method="POST"):
    body = json.dumps(data) if data is not None and not isinstance(data, str) else data
    return {"source": "dynamic", "method": method, "status": 200,
            "url": BASE + path, "post_data": body, "request_index": 0}


@pytest.mark.parametrize("payload", [
    {"query": "shoes"}, {"query": "sort by price"},
    {"query": "queryable book"}, {"query": "hello", "operationName": "Search"},
])
def test_rest_search_request_is_not_graphql(payload):
    assert not is_graphql_request(BASE + "/api/search", json.dumps(payload))
    assert normalize_candidates([candidate("/api/search", payload)])[0]["method"] == "POST"


def test_graphql_query_types_and_secret_values_not_exported():
    secret = "DO-NOT-EXPORT-THIS-VARIABLE"
    data = {
        "query": "query GetUser($id: ID!) { user(id: $id) { id } }",
        "operationName": "GetUser",
        "variables": {"id": secret, "limit": 3, "active": True},
    }
    result = normalize_candidates([candidate("/api/execute", data)])
    row = result[0]
    assert row["method"] == "GQL"
    assert row["note"] == "GraphQL query GetUser observed"
    types = {part["name"]: part["type"] for part in row["params"]["body"]}
    assert types["variables.id"] == "string"
    assert types["variables.limit"] == "integer"
    assert types["variables.active"] == "boolean"
    assert secret not in json.dumps(row)


def test_anonymous_query_and_raw_mutation():
    assert is_graphql_request(BASE + "/rpc", "{ viewer { id } }")
    assert operation_note(BASE + "/rpc", "{ viewer { id } }") == "GraphQL query observed"
    assert operation_note(BASE + "/rpc", "mutation Update { updateStatus }") == (
        "GraphQL mutation Update observed")


def test_url_encoded_get_graphql_operation():
    url = BASE + "/query?" + urlencode({"query": "subscription Events { events { id } }"})
    assert is_graphql_request(url)
    row = normalize_candidates([{"source": "dynamic", "method": "GET",
                                 "url": url, "status": 200, "request_index": 0}])[0]
    assert row["method"] == "GQL"
    assert "subscription Events" in row["note"]


def test_persisted_graphql_hash_not_in_note():
    sha = "f" * 64
    data = {"extensions": {"persistedQuery": {"version": 1, "sha256Hash": sha}}}
    row = normalize_candidates([candidate("/api/gateway", data)])[0]
    assert row["method"] == "GQL"
    assert row["note"] == "GraphQL persisted query observed"
    assert sha not in row["note"]


def test_untrusted_operation_name_and_browser_note_not_exported():
    private = "person@example.com token SECRET"
    data = {"query": "query { viewer { id } }", "operationName": private}
    row = candidate("/graphql", data)
    row["note"] = f"GraphQL {private}"
    result = normalize_candidates([row])[0]
    assert private not in result["note"]
    assert result["note"] == "GraphQL query observed"


def test_raw_graphql_text_never_becomes_a_body_field_name():
    private = "SENSITIVE-DOCUMENT-CONTENT"
    row = normalize_candidates([candidate(
        "/api/execute", "mutation Send { send(value: \"SENSITIVE-DOCUMENT-CONTENT\") }"
    )])[0]
    assert row["method"] == "GQL"
    assert all(private not in field["name"] for field in row["params"]["body"])
    assert row["params"]["body"][0]["name"] == "query"


def test_old_browser_gql_false_positive_uses_real_http_method():
    rows = from_network_records([{
        "resource_type": "fetch", "url": BASE + "/api/search",
        "method": "GQL", "http_method": "POST", "status": 200, "request_index": 1,
        "post_data": '{"query":"shoes"}',
    }])
    assert rows[0]["http_method"] == "POST"
    assert normalize_candidates(rows)[0]["method"] == "POST"


def test_variable_types_only_not_values():
    payload = json.dumps({"variables": {"payload": {"secret": "hidden"}, "count": 2}})
    assert observed_variable_types(payload) == [("count", "integer"), ("payload", "object")]
