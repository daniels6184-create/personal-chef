"""Profile, body measurements and nutrition targets.

Target rules (from the approved spec):
  * a target is created only as 'proposed';
  * it becomes 'active' only through POST /targets/{id}/approve with {"confirm": true};
  * approving supersedes the previous active target in the same transaction;
  * nothing edits or deletes an active or historical target.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .db import get_db
from .models import BodyMeasurement, Profile, TargetVersion
from .schemas import Decision, MeasurementIn, MeasurementOut, ProfileIn, ProfileOut, TargetIn, TargetOut
from .security import now, require_user

router = APIRouter(prefix="/api", tags=["profile"], dependencies=[Depends(require_user)])


# ------------------------------------------------------------------ profile

def _profile(db: Session) -> Profile:
    p = db.get(Profile, 1)
    if p is None:
        raise HTTPException(500, "Profile row missing: run the migrations.")
    return p


@router.get("/profile", response_model=ProfileOut)
def get_profile(db: Session = Depends(get_db)):
    return _profile(db)


@router.put("/profile", response_model=ProfileOut)
def put_profile(body: ProfileIn, db: Session = Depends(get_db)):
    p = _profile(db)
    data = body.model_dump(mode="json")
    p.display_name = body.display_name
    p.birth_date = body.birth_date
    p.sex = body.sex
    p.height_cm = body.height_cm
    p.preferences = data["preferences"]
    db.commit()
    db.refresh(p)
    return p


# ------------------------------------------------------------------ measurements

@router.get("/measurements", response_model=list[MeasurementOut])
def list_measurements(db: Session = Depends(get_db)):
    return db.scalars(select(BodyMeasurement).order_by(BodyMeasurement.measured_on.desc(),
                                                       BodyMeasurement.created_at.desc())).all()


@router.post("/measurements", response_model=MeasurementOut, status_code=201)
def add_measurement(body: MeasurementIn, db: Session = Depends(get_db)):
    m = BodyMeasurement(**body.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.put("/measurements/{mid}", response_model=MeasurementOut)
def edit_measurement(mid: uuid.UUID, body: MeasurementIn, db: Session = Depends(get_db)):
    m = db.get(BodyMeasurement, mid)
    if m is None:
        raise HTTPException(404, "No such measurement.")
    for k, v in body.model_dump().items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return m


@router.delete("/measurements/{mid}")
def delete_measurement(mid: uuid.UUID, db: Session = Depends(get_db)):
    m = db.get(BodyMeasurement, mid)
    if m is None:
        raise HTTPException(404, "No such measurement.")
    db.delete(m)
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ targets

@router.get("/targets", response_model=list[TargetOut])
def list_targets(db: Session = Depends(get_db)):
    order = {"active": 0, "proposed": 1, "superseded": 2, "rejected": 3}
    rows = db.scalars(select(TargetVersion).order_by(TargetVersion.created_at.desc())).all()
    return sorted(rows, key=lambda t: order.get(t.status, 9))


@router.get("/targets/active", response_model=TargetOut)
def active_target(db: Session = Depends(get_db)):
    t = db.scalar(select(TargetVersion).where(TargetVersion.status == "active"))
    if t is None:
        raise HTTPException(404, "No confirmed target yet.")
    return t


@router.post("/targets/proposals", response_model=TargetOut, status_code=201)
def propose_target(body: TargetIn, db: Session = Depends(get_db)):
    t = TargetVersion(**body.model_dump(mode="json", exclude={"effective_from"}),
                      effective_from=body.effective_from, status="proposed", origin="manual")
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _pending(db: Session, tid: uuid.UUID) -> TargetVersion:
    t = db.get(TargetVersion, tid, with_for_update=True)
    if t is None:
        raise HTTPException(404, "No such target.")
    if t.status != "proposed":
        raise HTTPException(409, f"This target is {t.status}; only proposals can be decided.")
    return t


@router.post("/targets/{tid}/approve", response_model=TargetOut)
def approve_target(tid: uuid.UUID, body: Decision, db: Session = Depends(get_db)):
    t = _pending(db, tid)
    current = db.scalar(select(TargetVersion).where(TargetVersion.status == "active").with_for_update())
    if current is not None:
        db.execute(update(TargetVersion).where(TargetVersion.id == current.id)
                   .values(status="superseded", decided_at=now()))
        db.flush()   # the partial unique index allows one active row
        t.supersedes_id = current.id
    t.status = "active"
    t.decided_at = now()
    db.commit()
    db.refresh(t)
    return t


@router.post("/targets/{tid}/reject", response_model=TargetOut)
def reject_target(tid: uuid.UUID, body: Decision, db: Session = Depends(get_db)):
    t = _pending(db, tid)
    t.status = "rejected"
    t.decided_at = now()
    db.commit()
    db.refresh(t)
    return t
