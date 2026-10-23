import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="grsn_test_"))
os.environ.update({
    "DATABASE_URL": f"sqlite:///{(_tmp / 'test.db').as_posix()}",
    "LLM_PROVIDER": "mock",
    "SEED_DEMO": "false",
    "STORAGE_DIR": str(_tmp / "storage"),
    "BACKUP_DIR": str(_tmp / "storage" / "backups"),
    "JWT_SECRET": "test-secret-test-secret-test-secret-123",
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import ensure_admin, upsert_dictionaries  # noqa: E402

Base.metadata.create_all(engine)
with SessionLocal() as _db:
    upsert_dictionaries(_db)
    ensure_admin(_db)


@pytest.fixture()
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture()
def client():
    return TestClient(app)


_counter = [0]


@pytest.fixture()
def user_token(client):
    _counter[0] += 1
    email = f"user{_counter[0]}@test.ru"
    r = client.post("/api/v1/auth/register", json={"name": "Тест", "email": email, "password": "Passw0rd1"})
    assert r.status_code == 201, r.text
    return r.json()["accessToken"]


@pytest.fixture()
def admin_token(client):
    r = client.post("/api/v1/auth/login", json={"email": "admin@grsn.local", "password": "Admin12345"})
    assert r.status_code == 200, r.text
    return r.json()["accessToken"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
