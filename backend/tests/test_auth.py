from tests.conftest import CSRF, PASSWORD


def test_everything_private_without_session(client):
    for path in ["/api/profile", "/api/targets", "/api/measurements", "/api/export",
                 "/api/targets/active", "/api/auth/passkeys"]:
        assert client.get(path).status_code == 401, path


def test_wrong_password_rejected(client):
    r = client.post("/api/auth/login", json={"password": "nope"}, headers=CSRF)
    assert r.status_code == 401
    assert client.get("/api/profile").status_code == 401


def test_login_sets_httponly_session_and_logout_ends_it(client):
    r = client.post("/api/auth/login", json={"password": PASSWORD}, headers=CSRF)
    assert r.status_code == 200
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert client.get("/api/profile").status_code == 200
    assert client.get("/api/auth/status").json()["signed_in"] is True
    client.post("/api/auth/logout", headers=CSRF)
    assert client.get("/api/profile").status_code == 401


def test_forged_cookie_rejected(client):
    client.cookies.set("pc_session", "made-up-token")
    assert client.get("/api/profile").status_code == 401


def test_rate_limit_after_five_failures(client):
    for _ in range(5):
        assert client.post("/api/auth/login", json={"password": "x"}, headers=CSRF).status_code == 401
    r = client.post("/api/auth/login", json={"password": PASSWORD}, headers=CSRF)
    assert r.status_code == 429   # even the right password waits out the window


def test_post_without_csrf_header_refused(client):
    r = client.post("/api/auth/login", json={"password": PASSWORD})
    assert r.status_code == 403


def test_cross_origin_post_refused(client):
    r = client.post("/api/auth/login", json={"password": PASSWORD},
                    headers={**CSRF, "Origin": "https://evil.example"})
    assert r.status_code == 403


def test_locked_when_no_password(client, monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "app_password", "")
    r = client.post("/api/auth/login", json={"password": ""}, headers=CSRF)
    assert r.status_code in (422, 503)
    assert client.get("/api/auth/status").json()["locked"] is True


def test_passkey_options_require_sign_in(client):
    assert client.post("/api/auth/passkeys/register/options", headers=CSRF).status_code == 401


def test_passkey_registration_options_and_bad_response(signed_in):
    r = signed_in.post("/api/auth/passkeys/register/options", headers=CSRF)
    assert r.status_code == 200
    opts = r.json()
    assert opts["rp"]["id"] == "testserver"
    assert opts["authenticatorSelection"]["residentKey"] == "required"
    bad = signed_in.post("/api/auth/passkeys/register/verify", json={"id": "x"}, headers=CSRF)
    assert bad.status_code == 400
    # the challenge is single-use
    again = signed_in.post("/api/auth/passkeys/register/verify", json={"id": "x"}, headers=CSRF)
    assert again.status_code == 400


def test_passkey_login_unknown_credential(client):
    assert client.post("/api/auth/passkeys/login/options", headers=CSRF).status_code == 200
    r = client.post("/api/auth/passkeys/login/verify", json={"id": "unknown"}, headers=CSRF)
    assert r.status_code == 401


def test_security_headers(client):
    r = client.get("/healthz")
    assert r.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert client.get("/api/auth/status").headers["cache-control"] == "no-store"
