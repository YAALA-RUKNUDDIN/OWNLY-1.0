"""Test fixtures. Tests run against the dockerized Postgres using a
dedicated test database (set TEST_DATABASE_URL or the default below)."""
import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg2://ownly:ownly_secret@localhost:5432/ownly_test"),
)
os.environ.setdefault("STORAGE_PROVIDER", "local")
os.environ.setdefault("STORAGE_LOCAL_PATH", "./test_storage")
os.environ.setdefault("PUSH_PROVIDER", "noop")

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.main import create_app  # noqa: E402
from app import models  # noqa: E402, F401


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(setup_database):
    app = create_app()
    # Skip table re-creation in lifespan (already handled by setup_database)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers(client):
    """Register a fresh user and return Authorization headers."""
    import uuid
    suffix = uuid.uuid4().hex[:8]
    resp = client.post("/api/v1/auth/register", json={
        "name": "Test User",
        "email": f"user_{suffix}@example.com",
        "password": "strongpassword1",
    })
    assert resp.status_code == 201, resp.text
    tokens = resp.json()["tokens"]
    return {"Authorization": f"Bearer {tokens['access_token']}"}, tokens["refresh_token"]


@pytest.fixture
def second_auth_headers(client):
    import uuid
    suffix = uuid.uuid4().hex[:8]
    resp = client.post("/api/v1/auth/register", json={
        "name": "Other User",
        "email": f"other_{suffix}@example.com",
        "password": "strongpassword1",
    })
    assert resp.status_code == 201, resp.text
    tokens = resp.json()["tokens"]
    # Same tuple shape as auth_headers so tests can unpack uniformly.
    return {"Authorization": f"Bearer {tokens['access_token']}"}, tokens["refresh_token"]