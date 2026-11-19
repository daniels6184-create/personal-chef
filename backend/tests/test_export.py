import json

from tests.conftest import CSRF


def test_export_contains_all_user_data_and_no_secrets(signed_in):
    signed_in.post("/api/measurements", json={"measured_on": "2026-11-19", "weight_kg": "80"}, headers=CSRF)
    r = signed_in.get("/api/export")
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    data = r.json()
    assert data["format"] == 1
    assert len(data["profile"]) == 1 and data["profile"][0]["display_name"] == "Dan"
    assert len(data["body_measurements"]) == 2
    assert data["targets"][0]["kcal"] == 3455
    text = json.dumps(data)
    for leak in ("token_hash", "public_key", "correct horse", "login_attempt"):
        assert leak not in text
