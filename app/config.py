from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./pcf.db"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_task_always_eager: bool = True

    object_storage_backend: str = "local"
    object_storage_local_dir: Path = Path("./data/objects")
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "pcfadmin"
    s3_secret_key: str = "change-me"
    s3_bucket: str = "pcf-artifacts"
    s3_region: str = "us-east-1"

    openlca_engine: str = "mock"
    openlca_url: str = "http://localhost:8080"
    openlca_api_token: str | None = None
    openlca_timeout_seconds: int = 600
    openlca_product_system_id: str | None = None
    openlca_impact_method_id: str | None = None

    oidc_enabled: bool = False
    oidc_issuer: str | None = None
    oidc_audience: str = "pcf-api"
    oidc_jwks_url: str | None = None
    local_auth_enabled: bool = True
    pcf_source_root: Path = Path("..")

    app_version: str = "0.1.0"
    git_commit: str = "uncommitted"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

