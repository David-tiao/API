"""Official JSONL phase enum with honest internal subphases."""
import json

from api_extractor.jsonl_logger import JsonlLogger


def read_rows(file):
    return [json.loads(line) for line in file.read_text().splitlines() if line.strip()]


def test_standard_phases_unchanged(tmp_path):
    path = tmp_path / "tool.log"
    logger = JsonlLogger(path)
    try:
        for phase in ("static", "dynamic", "verify"):
            logger.write("GET", "https://app.example.com/api/items", 200, phase)
    finally:
        logger.close()
    rows = read_rows(path)
    assert [row["phase"] for row in rows] == ["static", "dynamic", "verify"]
    assert all("detail_phase" not in row for row in rows)


def test_probe_and_redirect_are_mapped_but_original_statuses_preserved(tmp_path):
    path = tmp_path / "tool.log"
    logger = JsonlLogger(path)
    try:
        logger.write("GET", "https://app.example.com/api/items", 200, "probe",
                     resource_type="explicit_safe_get", request_index=0)
        logger.write("POST", "https://app.example.com/api/session", 303, "redirect")
        logger.write("GET", "https://app.example.com/dashboard", 200, "redirect")
    finally:
        logger.close()
    rows = read_rows(path)
    assert [(row["phase"], row.get("detail_phase"), row["status"]) for row in rows] == [
        ("verify", "probe", 200),
        ("dynamic", "redirect", 303),
        ("dynamic", "redirect", 200),
    ]
    assert rows[0]["request_index"] == 0
    assert rows[0]["resource_type"] == "explicit_safe_get"
    assert all(row["phase"] in {"static", "dynamic", "verify"} for row in rows)


def test_unknown_internal_phase_is_not_a_public_enum(tmp_path):
    path = tmp_path / "tool.log"
    logger = JsonlLogger(path)
    try:
        logger.write("-", "https://app.example.com/", 0, "experimental")
    finally:
        logger.close()
    row = read_rows(path)[0]
    assert row["phase"] == "verify" and row["detail_phase"] == "experimental"


def test_sensitive_fields_do_not_leak_to_redacted_url(tmp_path):
    path = tmp_path / "tool.log"
    logger = JsonlLogger(path)
    try:
        logger.write("GET", "https://user:pw@app.example.com/api?token=secret", 200, "redirect")
    finally:
        logger.close()
    raw = path.read_text()
    assert "user:pw" not in raw and "token=secret" not in raw
    assert "detail_phase" in raw
