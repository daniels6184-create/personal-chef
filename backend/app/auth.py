"""Sign-in: the APP_PASSWORD, or a passkey registered while signed in. No registration of users."""
import datetime as dt
import json
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from webauthn import (generate_authentication_options, generate_registration_options, options_to_json,
                      verify_authentication_response, verify_registration_response)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.exceptions import WebAuthnException
from webauthn.helpers.structs import (AuthenticatorSelectionCriteria, PublicKeyCredentialDescriptor,
                                      ResidentKeyRequirement, UserVerificationRequirement)

from .config import get_settings
from .db import get_db
from .models import AppSession, PasskeyCredential, WebauthnChallenge
from .schemas import PasskeyName, PasswordLogin
from .security import (check_rate_limit, client_ip, end_session, now, password_matches, record_attempt,
                       require_user, start_session)

router = APIRouter(prefix="/api/auth", tags=["auth"])

CHALLENGE_COOKIE = "pc_wa"
USER_HANDLE = b"personal-chef-owner"   # one user, fixed handle


def _locked() -> None:
    if not get_settings().app_password:
        raise HTTPException(503, "The app is locked: set APP_PASSWORD on the server.")


@router.get("/status")
def status(request: Request, db: Session = Depends(get_db)):
    """Signed in or not, and whether a passkey exists. Never says anything else."""
    from .security import COOKIE, _hash
    token = request.cookies.get(COOKIE)
    sess = db.get(AppSession, _hash(token)) if token else None
    has_passkey = db.scalar(select(PasskeyCredential.credential_id).limit(1)) is not None
    return {"signed_in": bool(sess and sess.expires_at > now()),
            "passkey_available": has_passkey,
            "locked": not get_settings().app_password}


@router.post("/login")
def login(body: PasswordLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    _locked()
    ip = client_ip(request)
    check_rate_limit(db, ip)
    if not password_matches(body.password):
        record_attempt(db, ip, False)
        raise HTTPException(401, "Wrong password.")
    record_attempt(db, ip, True)
    start_session(db, response, request, "password")
    return {"ok": True}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    end_session(db, request, response)
    return {"ok": True}


# ------------------------------------------------------------------ passkeys

def _store_challenge(db: Session, response: Response, challenge: bytes, purpose: str) -> None:
    cid = secrets.token_urlsafe(24)
    db.execute(delete(WebauthnChallenge).where(WebauthnChallenge.expires_at < now()))
    db.add(WebauthnChallenge(id=cid, challenge=challenge, purpose=purpose,
                             expires_at=now() + dt.timedelta(minutes=5)))
    db.commit()
    response.set_cookie(CHALLENGE_COOKIE, cid, max_age=300, httponly=True,
                        secure=get_settings().cookie_secure, samesite="strict", path="/api/auth")


def _take_challenge(db: Session, request: Request, purpose: str) -> bytes:
    cid = request.cookies.get(CHALLENGE_COOKIE)
    row = db.get(WebauthnChallenge, cid) if cid else None
    if row is None or row.purpose != purpose or row.expires_at < now():
        raise HTTPException(400, "The passkey request expired. Try again.")
    challenge = row.challenge
    db.delete(row)   # single use
    db.commit()
    return challenge


@router.get("/passkeys")
def list_passkeys(_=Depends(require_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(PasskeyCredential).order_by(PasskeyCredential.created_at)).all()
    return [{"id": r.credential_id, "name": r.name, "created_at": r.created_at,
             "last_used_at": r.last_used_at} for r in rows]


@router.delete("/passkeys/{credential_id}")
def delete_passkey(credential_id: str, _=Depends(require_user), db: Session = Depends(get_db)):
    row = db.get(PasskeyCredential, credential_id)
    if row is None:
        raise HTTPException(404, "No such passkey.")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.post("/passkeys/register/options")
def register_options(response: Response, _=Depends(require_user), db: Session = Depends(get_db)):
    s = get_settings()
    existing = db.scalars(select(PasskeyCredential)).all()
    opts = generate_registration_options(
        rp_id=s.rp_id, rp_name="Personal Chef", user_id=USER_HANDLE, user_name="owner",
        user_display_name="Owner",
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED),
        exclude_credentials=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id))
                             for c in existing])
    _store_challenge(db, response, opts.challenge, "register")
    return json.loads(options_to_json(opts))


@router.post("/passkeys/register/verify")
async def register_verify(request: Request, _=Depends(require_user), db: Session = Depends(get_db)):
    s = get_settings()
    payload = await request.json()
    try:
        name = PasskeyName(name=request.query_params.get("name") or "Phone").name
    except ValueError:
        raise HTTPException(422, "Passkey name must be 1-80 characters.") from None
    challenge = _take_challenge(db, request, "register")
    try:
        v = verify_registration_response(credential=payload, expected_challenge=challenge,
                                         expected_rp_id=s.rp_id, expected_origin=s.app_origin,
                                         require_user_verification=True)
    except (WebAuthnException, ValueError, KeyError, TypeError):
        raise HTTPException(400, "Passkey not accepted.") from None
    transports = payload.get("response", {}).get("transports", []) if isinstance(payload, dict) else []
    db.add(PasskeyCredential(credential_id=bytes_to_base64url(v.credential_id),
                             public_key=v.credential_public_key, sign_count=v.sign_count,
                             transports=[t for t in transports if isinstance(t, str)][:8], name=name))
    db.commit()
    return {"ok": True}


@router.post("/passkeys/login/options")
def login_options(response: Response, db: Session = Depends(get_db)):
    _locked()
    s = get_settings()
    opts = generate_authentication_options(rp_id=s.rp_id,
                                           user_verification=UserVerificationRequirement.REQUIRED)
    _store_challenge(db, response, opts.challenge, "login")
    return json.loads(options_to_json(opts))


@router.post("/passkeys/login/verify")
async def login_verify(request: Request, response: Response, db: Session = Depends(get_db)):
    _locked()
    s = get_settings()
    ip = client_ip(request)
    check_rate_limit(db, ip)
    payload = await request.json()
    challenge = _take_challenge(db, request, "login")
    cred = db.get(PasskeyCredential, str(payload.get("id", ""))) if isinstance(payload, dict) else None
    if cred is None:
        record_attempt(db, ip, False)
        raise HTTPException(401, "That passkey is not registered here.")
    try:
        v = verify_authentication_response(credential=payload, expected_challenge=challenge,
                                           expected_rp_id=s.rp_id, expected_origin=s.app_origin,
                                           credential_public_key=cred.public_key,
                                           credential_current_sign_count=cred.sign_count,
                                           require_user_verification=True)
    except (WebAuthnException, ValueError, KeyError, TypeError):
        record_attempt(db, ip, False)
        raise HTTPException(401, "Passkey check failed.") from None
    cred.sign_count = v.new_sign_count
    cred.last_used_at = now()
    db.commit()
    record_attempt(db, ip, True)
    start_session(db, response, request, "passkey")
    return {"ok": True}
