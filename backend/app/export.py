"""Full data export as one JSON document. Auth tables (sessions, passkeys, login attempts) are
left out: they are security records, not your data, and are useless anywhere else."""
import datetime as dt

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import BodyMeasurement, Profile, TargetVersion
from .security import require_user

router = APIRouter(prefix="/api", tags=["export"], dependencies=[Depends(require_user)])

EXPORT_FORMAT = 1
# Later stages add their tables here (recipes, diary, plans, pantry, shopping, feedback).
EXPORTED = {"profile": Profile, "body_measurements": BodyMeasurement, "targets": TargetVersion}


def _row(obj) -> dict:
    out = {}
    for col in sa_inspect(obj).mapper.column_attrs:
        v = getattr(obj, col.key)
        if isinstance(v, (dt.date, dt.datetime)):
            v = v.isoformat()
        elif v is not None and not isinstance(v, (str, int, float, bool, dict, list)):
            v = str(v)   # Decimal, UUID
        out[col.key] = v
    return out


def build_export(db: Session) -> dict:
    data = {"format": EXPORT_FORMAT, "app": "personal-chef",
            "exported_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    for name, model in EXPORTED.items():
        data[name] = [_row(r) for r in db.scalars(select(model)).all()]
    return data


@router.get("/export")
def export_all(db: Session = Depends(get_db)):
    stamp = dt.date.today().isoformat()
    return JSONResponse(build_export(db), headers={
        "Content-Disposition": f'attachment; filename="personal-chef-export-{stamp}.json"',
        "Cache-Control": "no-store"})
