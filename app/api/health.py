from fastapi import APIRouter
from sqlalchemy import text

from app.db import engine
from app.engines import get_calculation_engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.get("/health/openlca")
def openlca_health():
    return get_calculation_engine().health()

