import httpx
from celery.utils.log import get_task_logger

from app.celery_app import celery
from app.core.db import SessionLocal, UnitOfWork
from app.core.exceptions import ExternalServiceError
from app.core.metrics import TASK_RETRIES
from app.core.request_context import bind_context, reset_context
from app.services.calculation_service import CalculationService
from app.services.outbox_service import OutboxService

logger = get_task_logger(__name__)


@celery.task(
    bind=True,
    name="pcf.calculate",
    max_retries=2,
)
def calculate_run(self, run_id: str) -> str:
    headers = getattr(self.request, "headers", None) or {}
    tokens = bind_context(
        request_id=headers.get("request_id"),
        calculation_id=run_id,
        task_id=getattr(self.request, "id", None),
    )
    try:
        with SessionLocal() as db, UnitOfWork(db) as uow:
            token = CalculationService(db).claim_run(run_id)
            uow.commit()
        if token is None:
            logger.info("Ignoring duplicate calculation delivery for %s", run_id)
            return run_id
        logger.info("Executing PCF calculation %s", run_id)
        try:
            with SessionLocal() as db, UnitOfWork(db):
                CalculationService(db).execute(run_id)
        except Exception as exc:
            retryable = isinstance(
                exc,
                (ConnectionError, TimeoutError, httpx.TransportError),
            ) or (
                isinstance(exc, ExternalServiceError)
                and exc.code in {"OPENLCA_TIMEOUT", "OPENLCA_UNREACHABLE"}
            )
            exhausted = self.request.retries >= self.max_retries
            with SessionLocal() as db, UnitOfWork(db):
                CalculationService(db).mark_failed(
                    run_id,
                    exc,
                    retry=retryable and not exhausted,
                )
            if retryable and not exhausted:
                TASK_RETRIES.labels("pcf.calculate").inc()
                raise self.retry(
                    exc=exc,
                    countdown=2 ** (self.request.retries + 1),
                ) from exc
            raise
    finally:
        reset_context(tokens)
    return run_id


@celery.task(name="pcf.dispatch_outbox")
def dispatch_outbox() -> int:
    published = 0
    with SessionLocal() as db, UnitOfWork(db):
        service = OutboxService(db)
        for event in service.pending():
            try:
                calculate_run.apply_async(
                    args=[event.aggregate_id],
                    headers={"request_id": event.payload.get("request_id")},
                )
                service.mark_published(event)
                published += 1
            except Exception as exc:
                service.mark_failed(event, exc)
                logger.exception("Failed to publish outbox event %s", event.id)
    return published


@celery.task(name="pcf.recover_stale_calculations")
def recover_stale_calculations() -> int:
    with SessionLocal() as db, UnitOfWork(db):
        return OutboxService(db).recover_stale_calculations()
