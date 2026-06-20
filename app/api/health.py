from fastapi import APIRouter, Depends, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import func, select, text

from app.config import settings
from app.core.dependencies import calculation_engine, object_storage
from app.core.metrics import CALCULATION_STATUS
from app.db import SessionLocal, engine
from app.engines.base import CalculationEngine
from app.models import CalculationRun
from app.storage import ObjectStorage

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.get("/health/live")
def liveness():
    return {"status": "ok"}


@router.get("/health/ready")
def readiness(storage: ObjectStorage = Depends(object_storage)):
    checks: dict[str, dict] = {}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as exc:
        checks["database"] = {"status": "error", "error": str(exc)}
    try:
        checks["object_storage"] = storage.health()
    except Exception as exc:
        checks["object_storage"] = {"status": "error", "error": str(exc)}
    if settings.celery_task_always_eager:
        checks["task_broker"] = {"status": "ok", "mode": "eager"}
    else:
        try:
            import redis

            redis.Redis.from_url(settings.celery_broker_url).ping()
            checks["task_broker"] = {"status": "ok"}
        except Exception as exc:
            checks["task_broker"] = {"status": "error", "error": str(exc)}
    if any(check["status"] != "ok" for check in checks.values()):
        raise HTTPException(status_code=503, detail={"status": "error", "checks": checks})
    return {"status": "ok", "checks": checks}


@router.get("/health/openlca")
def openlca_health(calculator: CalculationEngine = Depends(calculation_engine)):
    return calculator.health()


@router.get("/metrics", include_in_schema=False)
def metrics():
    with SessionLocal() as db:
        rows = db.execute(
            select(CalculationRun.status, func.count()).group_by(CalculationRun.status)
        )
        CALCULATION_STATUS.clear()
        for status, count in rows:
            CALCULATION_STATUS.labels(status.value).set(count)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
