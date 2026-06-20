from celery import Celery

from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()

celery = Celery(
    "pcf",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery.conf.update(
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=True,
    task_time_limit=settings.openlca_timeout_seconds,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_hijack_root_logger=False,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "dispatch-pcf-outbox": {
            "task": "pcf.dispatch_outbox",
            "schedule": 5.0,
        },
        "recover-stale-pcf-calculations": {
            "task": "pcf.recover_stale_calculations",
            "schedule": 60.0,
        },
    },
)
celery.autodiscover_tasks(["app"])
