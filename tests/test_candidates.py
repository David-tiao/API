"""V10 candidate adapters: offline tests without any site or browser."""
from copy import deepcopy
from api_extractor.candidates import from_html_forms, from_network_records


def test_forms_preserve_fields_and_evidence_path():
    forms=[{"method":"POST","url":"https://example.test/submit","file":"evidence/pages/x.html",
            "fields":[{"name":"email"},{"name":"age"}]}]
    row=from_html_forms(forms)[0]
    assert row["body_fields"]==["email","age"]
    assert row["file"]=="evidence/pages/x.html"
    assert row["confidence"]==0.58


def test_forms_ignore_missing_url_and_malformed_fields():
    rows=from_html_forms([{"url":"","fields":[]},
                          {"url":"https://app.test/form","fields":[{},123,{"name":"ok"}]}])
    assert len(rows)==1 and rows[0]["body_fields"]==["ok"]


def test_browser_resource_filter_excludes_scripts():
    records=[{"url":"https://a.test/app.js","resource_type":"script"},
             {"url":"https://a.test/api","resource_type":"fetch"}]
    assert [r["url"] for r in from_network_records(records)]==["https://a.test/api"]


def test_all_supported_protocols_kept():
    rows=[{"url":"https://a.test/"+kind,"resource_type":kind}
          for kind in ("fetch","xhr","eventsource","websocket")]
    assert len(from_network_records(rows))==4


def test_status_and_request_index_preserved():
    row=from_network_records([{"url":"https://a.test/api","resource_type":"xhr",
                               "status":404,"request_index":7}])[0]
    assert row["status"]==404 and row["request_index"]==7


def test_graphql_method_not_converted_to_post():
    row=from_network_records([{"url":"https://a.test/graphql",
                               "resource_type":"fetch","http_method":"POST",
                               "method":"GQL"}])[0]
    assert row["method"]=="GQL"


def test_empty_network_url_ignored():
    assert from_network_records([{"url":"","resource_type":"xhr"}])==[]


def test_inputs_remain_unchanged():
    forms=[{"method":"POST","url":"https://a.test/form","fields":[{"name":"name"}]}]
    net=[{"url":"https://a.test/api","resource_type":"xhr","response_fields":["id"]}]
    forms_orig,net_orig=deepcopy(forms),deepcopy(net)
    from_html_forms(forms)
    from_network_records(net)
    assert forms==forms_orig and net==net_orig
