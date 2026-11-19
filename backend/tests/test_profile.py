import copy

from tests.conftest import CSRF


def test_seeded_profile_matches_spec(signed_in):
    p = signed_in.get("/api/profile").json()
    prefs = p["preferences"]
    assert p["height_cm"] == "188.0"
    assert prefs["proteins"]["preferred"] == ["chicken", "beef mince", "eggs"]
    assert "pork" in prefs["proteins"]["acceptable"]
    assert prefs["proteins"]["excluded_cuts"] == ["pork tenderloin"]
    assert prefs["limits"]["ingredient_caps_g_per_portion"] == {"spinach (raw)": 60}
    assert prefs["limits"]["gluten_meals_per_day_target"] == 1
    assert prefs["limits"]["gluten_meals_per_day_max"] == 2
    terms = {e["term"] for e in prefs["other_exclusions"]}
    assert {"cottage cheese", "kidney beans"} <= terms
    assert set(prefs["seafood"]["always_allowed_seasonings"]) == {"fish sauce", "oyster sauce"}
    assert prefs["seafood"]["occasional"] == ["tinned tuna"]
    assert "Italian" in prefs["taste"]["favourite_cuisines"]


def test_profile_edit_persists(signed_in):
    p = signed_in.get("/api/profile").json()
    body = {k: p[k] for k in ("display_name", "birth_date", "sex", "height_cm", "preferences")}
    body["preferences"]["limits"]["ingredient_caps_g_per_portion"]["spinach (raw)"] = 50
    body["preferences"]["taste"]["likes"].append("ragù")
    r = signed_in.put("/api/profile", json=body, headers=CSRF)
    assert r.status_code == 200, r.text
    again = signed_in.get("/api/profile").json()["preferences"]
    assert again["limits"]["ingredient_caps_g_per_portion"]["spinach (raw)"] == 50
    assert "ragù" in again["taste"]["likes"]


def test_profile_rejects_bad_values(signed_in):
    p = signed_in.get("/api/profile").json()
    base = {k: p[k] for k in ("display_name", "birth_date", "sex", "height_cm", "preferences")}

    bad = copy.deepcopy(base); bad["preferences"]["limits"]["gluten_meals_per_day_max"] = 0
    assert signed_in.put("/api/profile", json=bad, headers=CSRF).status_code == 422

    bad = copy.deepcopy(base); bad["preferences"]["surprise"] = "field"
    assert signed_in.put("/api/profile", json=bad, headers=CSRF).status_code == 422

    bad = copy.deepcopy(base); bad["height_cm"] = 900
    assert signed_in.put("/api/profile", json=bad, headers=CSRF).status_code == 422

    bad = copy.deepcopy(base); bad["display_name"] = "x" * 500
    r = signed_in.put("/api/profile", json=bad, headers=CSRF)
    assert r.status_code == 422 and "x" * 50 not in r.text   # values not echoed back


def test_measurements_crud(signed_in):
    rows = signed_in.get("/api/measurements").json()
    assert rows[0]["weight_kg"] == "79.55" and rows[0]["status"] == "verified"
    r = signed_in.post("/api/measurements", json={"measured_on": "2026-11-19", "weight_kg": "79.9",
                                                  "waist_cm": "82.0", "status": "stated"}, headers=CSRF)
    assert r.status_code == 201
    mid = r.json()["id"]
    assert signed_in.get("/api/measurements").json()[0]["id"] == mid
    r = signed_in.put(f"/api/measurements/{mid}", json={"measured_on": "2026-11-19", "weight_kg": "80.10"},
                      headers=CSRF)
    assert r.json()["weight_kg"] == "80.10"
    assert signed_in.delete(f"/api/measurements/{mid}", headers=CSRF).status_code == 200
    assert len(signed_in.get("/api/measurements").json()) == 1


def test_measurement_validation(signed_in):
    for body in [{"measured_on": "2026-11-19"},
                 {"measured_on": "2026-11-19", "weight_kg": "500"},
                 {"measured_on": "2099-01-01", "weight_kg": "80"},
                 {"measured_on": "2026-11-19", "weight_kg": "80", "status": "guessed"}]:
        assert signed_in.post("/api/measurements", json=body, headers=CSRF).status_code == 422, body
