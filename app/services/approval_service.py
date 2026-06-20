from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record_audit
from app.core.clock import Clock, SystemClock
from app.models import CalculationRun, CalculationStatus, Product


class ApprovalService:
    def __init__(self, db: Session, *, clock: Clock | None = None):
        self.db = db
        self.clock = clock or SystemClock()

    def submit(self, run: CalculationRun, actor: str) -> CalculationRun:
        if run.status != CalculationStatus.calculated:
            raise ValueError("Only calculated runs can be submitted")
        run.status = CalculationStatus.submitted
        run.submitted_by = actor
        run.submitted_at = self.clock.now()
        record_audit(
            self.db,
            actor=actor,
            action="calculation.submitted",
            object_type="calculation_run",
            object_id=run.id,
            before_hash=run.manifest_hash,
            after_hash=run.manifest_hash,
        )
        self.db.flush()
        return run

    def approve(self, run: CalculationRun, actor: str) -> CalculationRun:
        if run.status != CalculationStatus.submitted:
            raise ValueError("Only submitted runs can be approved")
        if actor == run.submitted_by:
            raise ValueError("Four-eyes rule: submitter cannot approve the same run")
        self.db.scalar(
            select(Product).where(Product.id == run.product_id).with_for_update()
        )
        approved_runs = list(
            self.db.scalars(
                select(CalculationRun)
                .where(
                    CalculationRun.product_id == run.product_id,
                    CalculationRun.status == CalculationStatus.approved,
                    CalculationRun.id != run.id,
                )
                .with_for_update()
            )
        )
        approved_ids = [item.id for item in approved_runs]
        for previous in approved_runs:
            previous.status = CalculationStatus.superseded
            record_audit(
                self.db,
                actor=actor,
                action="calculation.superseded",
                object_type="calculation_run",
                object_id=previous.id,
                before_hash=previous.manifest_hash,
                after_hash=previous.manifest_hash,
                details={"replacement_run_id": run.id},
            )
        self.db.flush()
        run.status = CalculationStatus.approved
        run.approved_by = actor
        run.approved_at = self.clock.now()
        record_audit(
            self.db,
            actor=actor,
            action="calculation.approved",
            object_type="calculation_run",
            object_id=run.id,
            before_hash=run.manifest_hash,
            after_hash=run.manifest_hash,
            details={"superseded_run_ids": approved_ids},
        )
        self.db.flush()
        return run

    def reject(self, run: CalculationRun, actor: str, reason: str) -> CalculationRun:
        if run.status != CalculationStatus.submitted:
            raise ValueError("Only submitted runs can be rejected")
        if actor == run.submitted_by:
            raise ValueError("Four-eyes rule: submitter cannot reject the same run")
        run.status = CalculationStatus.rejected
        run.approved_by = actor
        run.rejection_reason = reason
        record_audit(
            self.db,
            actor=actor,
            action="calculation.rejected",
            object_type="calculation_run",
            object_id=run.id,
            details={"reason": reason},
        )
        self.db.flush()
        return run
