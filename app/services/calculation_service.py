from __future__ import annotations

import time
import uuid
from decimal import Decimal

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, selectinload

from app.audit import record_audit
from app.config import settings
from app.core.clock import Clock, SystemClock
from app.core.exceptions import ConflictError
from app.core.metrics import CALCULATION_DURATION
from app.engines import get_calculation_engine
from app.engines.base import CalculationEngine
from app.models import (
    CalculationRun,
    CalculationSnapshot,
    CalculationStatus,
    ModelTemplate,
    ModelTemplateVersion,
    ResultContribution,
    ResultSummary,
)
from app.modules.calculations.contracts import CalculationInput, ModelTemplateConfig
from app.modules.snapshots.contracts import SnapshotPayload
from app.services.outbox_service import OutboxService
from app.storage import ObjectStorage, get_storage
from app.utils import canonical_json, hash_payload, sha256_bytes


class CalculationService:
    def __init__(
        self,
        db: Session,
        *,
        engine: CalculationEngine | None = None,
        storage: ObjectStorage | None = None,
        clock: Clock | None = None,
    ):
        self.db = db
        self.engine = engine or get_calculation_engine()
        self.storage = storage or get_storage()
        self.clock = clock or SystemClock()

    def create_run(
        self,
        *,
        snapshot: CalculationSnapshot,
        template_version: str,
        impact_method: str,
        idempotency_key: str,
        request_hash: str,
        actor: str,
        request_id: str | None = None,
    ) -> tuple[CalculationRun, bool]:
        existing = self.db.scalar(
            select(CalculationRun).where(CalculationRun.idempotency_key == idempotency_key)
        )
        if existing:
            if existing.request_hash and existing.request_hash != request_hash:
                raise ConflictError(
                    "Idempotency key was already used for a different calculation request",
                    code="IDEMPOTENCY_KEY_REUSED",
                )
            if not existing.request_hash:
                existing.request_hash = request_hash
            return existing, False
        template = self.db.scalar(
            select(ModelTemplateVersion)
            .join(ModelTemplate)
            .where(ModelTemplateVersion.version == template_version)
        )
        if not template:
            raise ValueError(f"Model template version not found: {template_version}")
        if not template.approved:
            raise ValueError(f"Model template version is not approved: {template_version}")
        run = CalculationRun(
            snapshot_id=snapshot.id,
            product_id=snapshot.product_id,
            model_template_version_id=template.id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            status=CalculationStatus.queued,
            impact_method=impact_method,
            requested_by=actor,
            engine=settings.openlca_engine,
        )
        self.db.add(run)
        self.db.flush()
        record_audit(
            self.db,
            actor=actor,
            action="calculation.queued",
            object_type="calculation_run",
            object_id=run.id,
            details={"snapshot_id": snapshot.id, "idempotency_key": idempotency_key},
        )
        OutboxService(self.db).enqueue_calculation(run.id, request_id)
        return run, True

    def claim_run(self, run_id: str) -> str | None:
        token = str(uuid.uuid4())
        now = self.clock.now()
        result = self.db.execute(
            update(CalculationRun)
            .where(
                CalculationRun.id == run_id,
                CalculationRun.status == CalculationStatus.queued,
            )
            .values(
                status=CalculationStatus.calculating,
                execution_token=token,
                attempt_count=CalculationRun.attempt_count + 1,
                heartbeat_at=now,
                started_at=now,
                completed_at=None,
                error=None,
            )
        )
        return token if result.rowcount == 1 else None

    def mark_failed(self, run_id: str, error: Exception, *, retry: bool) -> None:
        run = self.db.get(CalculationRun, run_id)
        if not run:
            return
        run.status = CalculationStatus.queued if retry else CalculationStatus.failed
        run.execution_token = None
        run.error = str(error)[:4000]
        run.completed_at = None if retry else self.clock.now()
        record_audit(
            self.db,
            actor="pcf-worker",
            action="calculation.retry_scheduled" if retry else "calculation.failed",
            object_type="calculation_run",
            object_id=run.id,
            details={"error": str(error), "attempt_count": run.attempt_count},
        )

    def execute(self, run_id: str) -> CalculationRun:
        run = self.db.scalar(
            select(CalculationRun)
            .options(selectinload(CalculationRun.summary), selectinload(CalculationRun.contributions))
            .where(CalculationRun.id == run_id)
        )
        if not run:
            raise ValueError(f"Calculation run not found: {run_id}")
        if run.status in {
            CalculationStatus.calculated,
            CalculationStatus.submitted,
            CalculationStatus.approved,
            CalculationStatus.superseded,
        }:
            return run
        snapshot = self.db.get(CalculationSnapshot, run.snapshot_id)
        template = self.db.get(ModelTemplateVersion, run.model_template_version_id)
        engine = self.engine
        started = time.perf_counter()
        try:
            result = engine.calculate(
                CalculationInput(
                    snapshot=SnapshotPayload.load_compatible(snapshot.payload),
                    impact_method=run.impact_method,
                ),
                ModelTemplateConfig(
                    product_system_uuid=template.product_system_uuid,
                    impact_method_uuid=template.impact_method_uuid,
                    database_version=template.database_version,
                    parameter_schema=template.parameter_schema,
                    parameter_contexts=template.parameter_schema.get("contexts", {}),
                    stage_process_uuids=template.parameter_schema.get(
                        "stage_process_uuids", {}
                    ),
                ),
            )
            self._assert_result_consistency(result)
            raw = {
                "engine": engine.name,
                "engine_version": result.engine_version,
                "total_kg_co2e": str(result.total_kg_co2e),
                "iso_categories": {k: str(v) for k, v in result.iso_categories.items()},
                "stages": {k: str(v) for k, v in result.stages.items()},
                "contributions": [
                    {
                        "dimension": x.dimension,
                        "code": x.code,
                        "name": x.name,
                        "amount_kg_co2e": str(x.amount_kg_co2e),
                        "metadata": x.metadata,
                    }
                    for x in result.contributions
                ],
                "raw": result.raw,
            }
            raw_key = f"calculations/{run.id}/openlca-result.json"
            raw_bytes = canonical_json(raw)
            self.storage.put(raw_key, raw_bytes, "application/json")
            if sha256_bytes(self.storage.get(raw_key)) != sha256_bytes(raw_bytes):
                raise RuntimeError("Stored openLCA result failed SHA-256 verification")
            self.db.execute(delete(ResultContribution).where(ResultContribution.run_id == run.id))
            if run.summary:
                self.db.delete(run.summary)
                self.db.flush()
            stages = result.stages
            iso = result.iso_categories
            self.db.add(
                ResultSummary(
                    run_id=run.id,
                    total_kg_co2e=result.total_kg_co2e,
                    functional_unit=snapshot.payload["functional_unit"],
                    boundary=snapshot.boundary,
                    impact_method=run.impact_method,
                    aircraft=iso.get("aircraft", Decimal("0")),
                    biogenic_emissions=iso.get("biogenic_emissions", Decimal("0")),
                    biogenic_removals=iso.get("biogenic_removals", Decimal("0")),
                    fossil=iso.get("fossil", Decimal("0")),
                    land_use_change=iso.get("land_use_change", Decimal("0")),
                    raw_materials=stages.get("raw_materials", Decimal("0")),
                    inbound_transport=stages.get("inbound_transport", Decimal("0")),
                    manufacturing=stages.get("manufacturing", Decimal("0")),
                    packaging=stages.get("packaging", Decimal("0")),
                    data_quality_status="integration_test" if engine.name == "mock" else "validated",
                )
            )
            for rank, item in enumerate(result.contributions, start=1):
                self.db.add(
                    ResultContribution(
                        run_id=run.id,
                        dimension=item.dimension,
                        code=item.code,
                        name=item.name,
                        amount_kg_co2e=item.amount_kg_co2e,
                        rank=rank,
                        metadata_json=item.metadata,
                    )
                )
            manifest = {
                "snapshot_manifest_hash": snapshot.manifest_hash,
                "template_version": template.version,
                "template_database_version": template.database_version,
                "impact_method": run.impact_method,
                "engine": engine.name,
                "engine_version": result.engine_version,
                "app_version": settings.app_version,
                "git_commit": settings.git_commit,
                "raw_result_sha256": hash_payload(raw),
                "result_total": str(result.total_kg_co2e),
            }
            run.status = CalculationStatus.calculated
            run.engine = engine.name
            run.engine_version = result.engine_version
            run.raw_result_object_key = raw_key
            run.completed_at = self.clock.now()
            run.heartbeat_at = run.completed_at
            run.execution_token = None
            run.manifest_hash = hash_payload(manifest)
            record_audit(
                self.db,
                actor="pcf-worker",
                action="calculation.completed",
                object_type="calculation_run",
                object_id=run.id,
                after_hash=run.manifest_hash,
                details=manifest,
            )
            CALCULATION_DURATION.labels(engine.name, "success").observe(
                time.perf_counter() - started
            )
            self.db.flush()
            return self.db.scalar(
                select(CalculationRun)
                .options(selectinload(CalculationRun.summary), selectinload(CalculationRun.contributions))
                .where(CalculationRun.id == run.id)
            )
        except Exception:
            CALCULATION_DURATION.labels(engine.name, "error").observe(
                time.perf_counter() - started
            )
            raise

    @staticmethod
    def _assert_result_consistency(result) -> None:
        tolerance = max(Decimal("0.01"), abs(result.total_kg_co2e) * Decimal("0.001"))
        stage_total = sum(result.stages.values(), Decimal("0"))
        if abs(stage_total - result.total_kg_co2e) > tolerance:
            raise RuntimeError(
                "Lifecycle stage contributions do not reconcile with the openLCA total; "
                "configure complete stage_process_uuids in the approved template"
            )
        iso_total = sum(result.iso_categories.values(), Decimal("0"))
        if abs(iso_total - result.total_kg_co2e) > tolerance:
            raise RuntimeError(
                "ISO 14067 category contributions do not reconcile with the openLCA total"
            )
