"""Authentication tests: registration, login, refresh rotation, logout."""
import uuid


def test_register_success(client):
    resp = client.post("/api/v1/auth/register", json={
        "name": "Alice", "email": f"alice_{uuid.uuid4().hex[:6]}@ownlymail.com", "password": "password123",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["user"]["name"] == "Alice"
    assert "access_token" in body["tokens"]
    assert "refresh_token" in body["tokens"]


def test_register_duplicate_email_conflict(client):
    email = f"dup_{uuid.uuid4().hex[:6]}@ownlymail.com"
    r1 = client.post("/api/v1/auth/register", json={"name": "A", "email": email, "password": "password123"})
    assert r1.status_code == 201
    r2 = client.post("/api/v1/auth/register", json={"name": "B", "email": email.upper(), "password": "password123"})
    assert r2.status_code == 409


def test_register_short_password_rejected(client):
    resp = client.post("/api/v1/auth/register", json={
        "name": "A", "email": f"short_{uuid.uuid4().hex[:6]}@ownlymail.com", "password": "short",
    })
    assert resp.status_code == 422


def test_login_success_and_wrong_password(client):
    email = f"login_{uuid.uuid4().hex[:6]}@ownlymail.com"
    client.post("/api/v1/auth/register", json={"name": "L", "email": email, "password": "password123"})
    ok = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    assert ok.status_code == 200
    bad = client.post("/api/v1/auth/login", json={"email": email, "password": "wrongpassword"})
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "unauthorized"


def test_refresh_rotation_and_reuse_detection(client):
    email = f"rot_{uuid.uuid4().hex[:6]}@ownlymail.com"
    reg = client.post("/api/v1/auth/register", json={"name": "R", "email": email, "password": "password123"})
    refresh_token = reg.json()["tokens"]["refresh_token"]

    # First refresh succeeds and returns a NEW refresh token
    r1 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert r1.status_code == 200
    new_refresh = r1.json()["refresh_token"]
    assert new_refresh != refresh_token

    # Reusing the OLD (revoked) token → family revoked → 401
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert r2.status_code == 401
    assert "reuse" in r2.json()["error"]["message"].lower()

    # Even the new token is now dead (family revoked)
    r3 = client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert r3.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me").json()["error"]["code"] == "unauthorized"


def test_me_with_token(client, auth_headers):
    headers, _ = auth_headers
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"].endswith("@ownlymail.com")


def test_logout_revokes_refresh(client):
    email = f"out_{uuid.uuid4().hex[:6]}@ownlymail.com"
    reg = client.post("/api/v1/auth/register", json={"name": "O", "email": email, "password": "password123"})
    tokens = reg.json()["tokens"]
    lo = client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert lo.status_code == 200
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 401