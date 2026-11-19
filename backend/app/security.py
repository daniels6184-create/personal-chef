"""Sessions, request-forgery protection, login rate limiting and security headers."""
import datetime as dt
import hashlib
import hmac
import secrets

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import AppSession, LoginAttempt

COOKIE = "pc_session"
CSRF_HEADER = "x-requested-with"
CSRF_VALUE = "personal-chef"

# Login throttling: per client IP, and overall (a single-user app has no reason for more).
MAX_FAILS_PER_IP = 5
MAX_FAILS_TOTAL = 20
WINDOW = dt.timedelta(minutes=15)


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def client_ip(request: Request) -> str:
    # Render puts the real client first in X-Forwarded-For.
    fwd = request.headers.get("x-forwarded-for", "")
    return (fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown"))[:64]


def password_matches(given: str) -> bool:
    expected = get_settings().app_password
    if not expected:
        return False
    # Compare digests so the comparison is constant-time regardless of length.
    return hmac.compare_digest(hashlib.sha256(given.encode()).digest(),
                               hashlib.sha256(expected.encode()).digest())


# ------------------------------------------------------------------ rate limiting

def check_rate_limit(db: Session, ip: str) -> None:
    since = now() - WINDOW
    ip_fails = db.scalar(select(func.count()).select_from(LoginAttempt).where(
        LoginAttempt.ip == ip, LoginAttempt.success.is_(False), LoginAttempt.at > since))
    all_fails = db.scalar(select(func.count()).select_from(LoginAttempt).where(
        LoginAttempt.success.is_(False), LoginAttempt.at > since))
    if ip_fails >= MAX_FAILS_PER_IP or all_fails >= MAX_FAILS_TOTAL:
        raise HTTPException(429, "Too many attempts. Wait 15 minutes and try again.")


def record_attempt(db: Session, ip: str, success: bool) -> None:
    db.add(LoginAttempt(ip=ip, success=success))
    # Housekeeping: nothing older than a day is needed.
    db.execute(delete(LoginAttempt).where(LoginAttempt.at < now() - dt.timedelta(days=1)))
    db.commit()


# ------------------------------------------------------------------ sessions

def start_session(db: Session, response: Response, request: Request, method: str) -> None:
    s = get_settings()
    token = secrets.token_urlsafe(32)
    db.add(AppSession(token_hash=_hash(token), method=method,
                      expires_at=now() + dt.timedelta(days=s.session_days),
                      device=request.headers.get("user-agent", "")[:120]))
    db.execute(delete(AppSession).where(AppSession.expires_at < now()))
    db.commit()
    response.set_cookie(COOKIE, token, max_age=s.session_days * 86400, httponly=True,
                        secure=s.cookie_secure, samesite="lax", path="/")


def end_session(db: Session, request: Request, response: Response) -> None:
    token = request.cookies.get(COOKIE)
    if token:
        db.execute(delete(AppSession).where(AppSession.token_hash == _hash(token)))
        db.commit()
    response.delete_cookie(COOKIE, path="/")


def current_session(request: Request, db: Session = Depends(get_db)) -> AppSession:
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "Sign in first.")
    sess = db.get(AppSession, _hash(token))
    if sess is None or sess.expires_at < now():
        raise HTTPException(401, "Your session has ended. Sign in again.")
    # Sliding expiry, written at most once an hour to keep database writes (and Neon wake-ups) low.
    if now() - sess.last_seen_at > dt.timedelta(hours=1):
        sess.last_seen_at = now()
        sess.expires_at = now() + dt.timedelta(days=get_settings().session_days)
        db.commit()
    return sess


require_user = current_session


# ------------------------------------------------------------------ CSRF

def csrf_guard(request: Request) -> None:
    """Every state-changing API call must carry a custom header. Browsers will not send one
    cross-site without a CORS preflight, which this app never grants. The Origin header, when
    present, must also be ours."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    if request.headers.get(CSRF_HEADER) != CSRF_VALUE:
        raise HTTPException(403, "Missing request header.")
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") != get_settings().app_origin.rstrip("/"):
        raise HTTPException(403, "Cross-site request refused.")


SECURITY_HEADERS = {
    "Content-Security-Policy": ("default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; "
                                "style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; "
                                "font-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
                                "form-action 'self'"),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "camera=(self), microphone=(), geolocation=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}
