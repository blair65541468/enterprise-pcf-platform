from celery import Celery

from app.config import settings

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
)
celery.autodiscover_tasks(["app"])

