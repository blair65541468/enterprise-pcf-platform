import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test-pcf.db"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["OBJECT_STORAGE_BACKEND"] = "local"
os.environ["OBJECT_STORAGE_LOCAL_DIR"] = "./test-objects"
os.environ["OPENLCA_ENGINE"] = "mock"
os.environ["LOCAL_AUTH_ENABLED"] = "true"

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-openlca",
        action="store_true",
        default=False,
        help="run integration tests against a configured real openLCA REST service",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-openlca"):
        return
    skip_openlca = pytest.mark.skip(
        reason="real openLCA integration tests require --run-openlca"
    )
    for item in items:
        if "openlca_integration" in item.keywords:
            item.add_marker(skip_openlca)


@pytest.fixture(autouse=True)
def clean_database(request):
    if request.node.get_closest_marker("openlca_integration"):
        yield
        return

    from app.db import Base, engine

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
    from app.db import SessionLocal

    with SessionLocal() as session:
        yield session


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


def auth(user: str, roles: str) -> dict[str, str]:
    return {"X-User-Id": user, "X-Roles": roles}
