import pytest
import redis
from sqlalchemy import inspect, text

from app.config import settings
from app.db import engine
from app.storage import get_storage

pytestmark = pytest.mark.infrastructure


def test_postgres_redis_storage_and_migration_head():
    assert not settings.database_url.startswith("sqlite")
    assert not settings.celery_task_always_eager
    assert settings.object_storage_backend == "s3"

    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
        tables = set(inspect(connection).get_table_names())
        assert "outbox_event" in tables
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0002_reliable_calculations"
        )

    assert redis.Redis.from_url(settings.celery_broker_url).ping()
    assert get_storage().health() == {"status": "ok", "backend": "s3"}
