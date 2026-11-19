"""Seed the profile, the 12 Nov weigh-in and the confirmed Phase 1 target (only into an empty DB).

Revision ID: 0002
Revises: 0001
"""
import json

import sqlalchemy as sa
from alembic import op

from app import seed
from app.schemas import Preferences

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    Preferences(**seed.PROFILE["preferences"])   # refuse to seed an invalid shape
    if conn.execute(sa.text("SELECT count(*) FROM profile")).scalar() == 0:
        p = seed.PROFILE
        conn.execute(sa.text(
            "INSERT INTO profile (id, display_name, birth_date, sex, height_cm, preferences, updated_at) "
            "VALUES (1, :n, :b, :s, :h, CAST(:p AS JSONB), now())"),
            {"n": p["display_name"], "b": p["birth_date"], "s": p["sex"], "h": p["height_cm"],
             "p": json.dumps(p["preferences"])})
    if conn.execute(sa.text("SELECT count(*) FROM body_measurement")).scalar() == 0:
        for m in seed.MEASUREMENTS:
            conn.execute(sa.text(
                "INSERT INTO body_measurement (id, measured_on, weight_kg, status, source, created_at) "
                "VALUES (gen_random_uuid(), :d, :w, :st, :src, now())"),
                {"d": m["measured_on"], "w": m["weight_kg"], "st": m["status"], "src": m["source"]})
    if conn.execute(sa.text("SELECT count(*) FROM target_version")).scalar() == 0:
        t = seed.ACTIVE_TARGET
        conn.execute(sa.text(
            "INSERT INTO target_version (id, phase, status, origin, kcal, protein_g, carbs_g, fat_g, fibre_g, "
            "day_types, rationale, effective_from, created_at, decided_at) VALUES (gen_random_uuid(), :phase, "
            ":status, :origin, :kcal, :p, :c, :f, :fi, CAST(:dt AS JSONB), :r, :ef, now(), now())"),
            {"phase": t["phase"], "status": t["status"], "origin": t["origin"], "kcal": t["kcal"],
             "p": t["protein_g"], "c": t["carbs_g"], "f": t["fat_g"], "fi": t["fibre_g"],
             "dt": json.dumps(t["day_types"]), "r": t["rationale"], "ef": t["effective_from"]})


def downgrade() -> None:
    pass   # never delete user data on downgrade
