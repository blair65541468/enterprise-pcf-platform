import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test-pcf.db"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["OBJECT_STORAGE_BACKEND"] = "local"
os.environ["OBJECT_STORAGE_LOCAL_DIR"] = "./test-objects"
os.environ["OPENLCA_ENGINE"] = "mock"
os.environ["LOCAL_AUTH_ENABLED"] = "true"

import pytest
from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    engine.dispose()
    for target in (Path("test-pcf.db"), Path("test-objects")):
        if target.is_file():
            target.unlink(missing_ok=True)
        elif target.is_dir():
            import shutil

            shutil.rmtree(target, ignore_errors=True)


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def auth(user: str, roles: str) -> dict[str, str]:
    return {"X-User-Id": user, "X-Roles": roles}
