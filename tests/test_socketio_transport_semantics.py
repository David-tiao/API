"""Socket.IO handshake semantics are explicit and never export frame contents."""
import json
from api_extractor.candidates import from_network_records
from api_extractor.normalization import normalize_candidates
from api_extractor.transport_semantics import socketio_transport_note

BASE = "https://shop.example.test"


def network(method, resource_type, transport, *, post_data=None):
    return {
        "source": "dynamic",
        "method": method,
        "http_method": "GET" if method == "WS" else method,
        "url": BASE + "/socket.io/?EIO=4&transport=" + transport + "&sid=PRIVATE_SESSION_ID",
        "resource_type": resource_type,
        "post_data": post_data,
        "status": 200 if method != "WS" else 101,
        "request_index": {"GET": 0, "POST": 1, "WS": 2}[method],
        "headers": {},
    }


def test_transport_labels_keep_wire_methods_and_distinguish_websocket():
    rows = normalize_candidates(from_network_records([
        network("GET", "fetch", "polling"),
        network("POST", "xhr", "polling"),
        network("WS", "websocket", "websocket"),
    ]))
    assert {r["method"] for r in rows} == {"GET", "POST", "WS"}
    by_method = {row["method"]: row for row in rows}
    assert "HTTP polling transport" in by_method["GET"]["note"]
    assert "HTTP polling transport" in by_method["POST"]["note"]
    assert "WebSocket transport handshake" in by_method["WS"]["note"]
    assert all("not business REST" in row["note"] for row in rows)
    assert all(len(row["evidence"]) == 1 for row in rows)


def test_opaque_polling_frames_not_exported_as_parameters_or_notes():
    secret = "DO_NOT_EXPORT_FRAME_PAYLOAD"
    frames = '42["user:event",{"token":"' + secret + '"}]'
    rows = normalize_candidates(from_network_records([
        network("POST", "fetch", "polling", post_data=frames),
    ]))
    assert len(rows) == 1
    assert rows[0]["params"]["body"] == []
    assert secret not in json.dumps(rows)
    assert "PRIVATE_SESSION_ID" not in json.dumps(rows)
    assert {p["name"] for p in rows[0]["params"]["query"]} == {
        "EIO", "transport", "sid",
    }


def test_transport_frame_signature_key_not_wrongly_inferred():
    row = network("POST", "fetch", "polling", post_data='40{"signature":"SECRET_FRAME"}')
    entry = normalize_candidates(from_network_records([row]))[0]
    assert entry["auth"] == "none"
    assert entry["params"]["body"] == []
    assert "Signing fields observed" not in entry["note"]


def test_normal_api_and_unverified_fake_socketio_patterns_untouched():
    normal = BASE + "/api/events?EIO=4&transport=polling"
    missing = BASE + "/socket.io/?transport=polling"
    assert socketio_transport_note(normal, "GET", "fetch") is None
    assert socketio_transport_note(missing, "GET", "fetch") is None
    assert socketio_transport_note(
        BASE + "/socket.io/?EIO=4&transport=websocket", "GET", "fetch"
    ) is None


def test_query_secret_not_exported_in_socketio_protocol_note():
    url = BASE + "/socket.io/?EIO=4&transport=polling&sid=PRIVATE_SID"
    note = socketio_transport_note(url, "GET", "xhr")
    assert note and "PRIVATE_SID" not in note
    assert "Socket.IO HTTP polling transport" in note


def test_unsupported_engine_frame_type_is_not_misclassified():
    assert socketio_transport_note(
        BASE + "/socket.io/?EIO=4&transport=polling", "WS", "websocket"
    ) is None
    assert socketio_transport_note(
        BASE + "/socket.io/?EIO=4&transport=websocket", "POST", "xhr"
    ) is None
