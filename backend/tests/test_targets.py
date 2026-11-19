from tests.conftest import CSRF

PHASE2 = {"phase": "fat_loss_maintain_muscle", "kcal": 3055, "protein_g": 190, "carbs_g": 400,
          "fat_g": 85, "rationale": "Example proposal", "effective_from": "2027-02-01",
          "day_types": {"rest": {"carbs_g": 330, "label": "Rest"},
                        "standard": {"carbs_g": 400, "label": "Standard"},
                        "long": {"carbs_g": 575, "label": "Long"}}}


def test_seeded_active_target(signed_in):
    t = signed_in.get("/api/targets/active").json()
    assert (t["kcal"], t["protein_g"], t["carbs_g"], t["fat_g"]) == (3455, 175, 475, 95)
    assert t["phase"] == "muscle_gain" and t["origin"] == "stated"
    assert {k: v["carbs_g"] for k, v in t["day_types"].items()} == {"rest": 400, "standard": 475, "long": 575}


def test_proposal_does_not_change_active_target(signed_in):
    r = signed_in.post("/api/targets/proposals", json=PHASE2, headers=CSRF)
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "proposed"
    assert signed_in.get("/api/targets/active").json()["kcal"] == 3455


def test_approval_needs_explicit_confirm(signed_in):
    pid = signed_in.post("/api/targets/proposals", json=PHASE2, headers=CSRF).json()["id"]
    assert signed_in.post(f"/api/targets/{pid}/approve", json={}, headers=CSRF).status_code == 422
    assert signed_in.post(f"/api/targets/{pid}/approve", json={"confirm": False}, headers=CSRF).status_code == 422
    assert signed_in.get("/api/targets/active").json()["kcal"] == 3455


def test_approve_supersedes_and_keeps_history(signed_in):
    old = signed_in.get("/api/targets/active").json()
    pid = signed_in.post("/api/targets/proposals", json=PHASE2, headers=CSRF).json()["id"]
    r = signed_in.post(f"/api/targets/{pid}/approve", json={"confirm": True}, headers=CSRF)
    assert r.status_code == 200 and r.json()["status"] == "active"
    assert r.json()["supersedes_id"] == old["id"]
    statuses = {t["id"]: t["status"] for t in signed_in.get("/api/targets").json()}
    assert statuses[old["id"]] == "superseded" and statuses[pid] == "active"
    assert list(statuses.values()).count("active") == 1
    # a decided target cannot be decided again
    assert signed_in.post(f"/api/targets/{pid}/approve", json={"confirm": True}, headers=CSRF).status_code == 409
    assert signed_in.post(f"/api/targets/{old['id']}/approve", json={"confirm": True},
                          headers=CSRF).status_code == 409


def test_reject(signed_in):
    pid = signed_in.post("/api/targets/proposals", json=PHASE2, headers=CSRF).json()["id"]
    r = signed_in.post(f"/api/targets/{pid}/reject", json={"confirm": True}, headers=CSRF)
    assert r.json()["status"] == "rejected"
    assert signed_in.get("/api/targets/active").json()["kcal"] == 3455


def test_inconsistent_macros_refused(signed_in):
    bad = dict(PHASE2, kcal=2500)   # 4*190 + 4*400 + 9*85 = 3,125, not 2,500
    r = signed_in.post("/api/targets/proposals", json=bad, headers=CSRF)
    assert r.status_code == 422


def test_standard_day_must_match_base(signed_in):
    bad = dict(PHASE2, day_types={"standard": {"carbs_g": 450, "label": "Standard"}})
    assert signed_in.post("/api/targets/proposals", json=bad, headers=CSRF).status_code == 422


def test_no_route_edits_or_deletes_targets(signed_in):
    tid = signed_in.get("/api/targets/active").json()["id"]
    assert signed_in.put(f"/api/targets/{tid}", json=PHASE2, headers=CSRF).status_code in (404, 405)
    assert signed_in.delete(f"/api/targets/{tid}", headers=CSRF).status_code in (404, 405)


def test_database_allows_only_one_active(signed_in):
    import pytest
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import IntegrityError

    from app.config import get_settings
    eng = create_engine(get_settings().sqlalchemy_url)
    with pytest.raises(IntegrityError), eng.begin() as c:
        c.execute(text("INSERT INTO target_version (id, phase, status, origin, kcal, protein_g, carbs_g, fat_g, "
                       "day_types, rationale, effective_from) VALUES (gen_random_uuid(), 'maintenance', "
                       "'active', 'manual', 3000, 150, 400, 90, '{}', '', '2027-01-01')"))
    eng.dispose()


def test_day_types_must_be_ordered(signed_in):
    bad = dict(PHASE2, day_types={"rest": {"carbs_g": 500, "label": "Rest"},
                                  "standard": {"carbs_g": 400, "label": "Standard"}})
    assert signed_in.post("/api/targets/proposals", json=bad, headers=CSRF).status_code == 422
