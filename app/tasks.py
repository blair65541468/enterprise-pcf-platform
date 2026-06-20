from celery.utils.log import get_task_logger
import httpx

from app.celery_app import celery
from app.db import SessionLocal
from app.services.calculation_service import CalculationService

logger = get_task_logger(__name__)


@celery.task(
    bind=True,
    name="pcf.calculate",
    autoretry_for=(ConnectionError, TimeoutError, httpx.TransportError),
    retry_backoff=True,
    max_retries=2,
)
def calculate_run(self, run_id: str) -> str:
    with SessionLocal() as db:
        logger.info("Executing PCF calculation %s", run_id)
        CalculationService(db).execute(run_id)
    return run_id
