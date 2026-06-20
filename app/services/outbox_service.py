from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import CalculationRun, CalculationStatus, OutboxEvent


class OutboxService:
    def __init__(self, db: Session):
        self.db = db

    def enqueue_calculation(self, run_id: str, request_id: str | None = None) -> OutboxEvent:
        existing = self.db.scalar(
            select(OutboxEvent).where(
                OutboxEvent.event_type == "calculation.requested",
                OutboxEvent.aggregate_id == run_id,
            )
        )
        if existing:
            existing.published_at = None
            existing.last_error = None
            existing.payload = {"run_id": run_id, "request_id": request_id}
            return existing
        event = OutboxEvent(
            event_type="calculation.requested",
            aggregate_type="calculation_run",
            aggregate_id=run_id,
            payload={"run_id": run_id, "request_id": request_id},
        )
        self.db.add(event)
        self.db.flush()
        return event

    def pending(self, limit: int | None = None) -> list[OutboxEvent]:
        return list(
            self.db.scalars(
                select(OutboxEvent)
                .where(OutboxEvent.published_at.is_(None))
                .order_by(OutboxEvent.created_at)
                .limit(limit or settings.outbox_batch_size)
            )
        )

    def mark_published(self, event: OutboxEvent) -> None:
        event.published_at = datetime.now(timezone.utc)
        event.attempt_count += 1
        event.last_error = None

    def mark_failed(self, event: OutboxEvent, error: Exception) -> None:
        event.attempt_count += 1
        event.last_error = str(error)[:2000]

    def recover_stale_calculations(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=settings.calculation_stale_seconds
        )
        runs = list(
            self.db.scalars(
                select(CalculationRun).where(
                    CalculationRun.status == CalculationStatus.calculating,
                    CalculationRun.heartbeat_at < cutoff,
                )
            )
        )
        for run in runs:
            run.status = CalculationStatus.queued
            run.execution_token = None
            self.enqueue_calculation(run.id)
        return len(runs)
