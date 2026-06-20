from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.modules.model_base import TimestampMixin, new_id, utcnow


class CalculationStatus(str, enum.Enum):
    draft = "draft"
    validated = "validated"
    queued = "queued"
    calculating = "calculating"
    calculated = "calculated"
    submitted = "submitted"
    approved = "approved"
    rejected = "rejected"
    superseded = "superseded"
    failed = "failed"


class CalculationSnapshot(Base, TimestampMixin):
    __tablename__ = "calculation_snapshot"
    __table_args__ = (UniqueConstraint("product_id", "version", name="uq_snapshot_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    product_id: Mapped[str] = mapped_column(ForeignKey("product.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    product_version_id: Mapped[str] = mapped_column(ForeignKey("product_version.id"))
    route_id: Mapped[str | None] = mapped_column(ForeignKey("process_route.id"))
    factor_set_version: Mapped[str] = mapped_column(String(100))
    boundary: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict] = mapped_column(JSON)
    manifest_hash: Mapped[str] = mapped_column(String(64), unique=True)
    validation_errors: Mapped[list] = mapped_column(JSON, default=list)
    created_by: Mapped[str] = mapped_column(String(100))


class CalculationRun(Base, TimestampMixin):
    __tablename__ = "calculation_run"
    __table_args__ = (
        Index(
            "uq_calculation_run_current_approved",
            "product_id",
            unique=True,
            postgresql_where=text("status = 'approved'"),
            sqlite_where=text("status = 'approved'"),
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("calculation_snapshot.id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("product.id"), index=True)
    model_template_version_id: Mapped[str] = mapped_column(
        ForeignKey("model_template_version.id")
    )
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True)
    request_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    status: Mapped[CalculationStatus] = mapped_column(
        Enum(CalculationStatus), default=CalculationStatus.draft, index=True
    )
    execution_token: Mapped[str | None] = mapped_column(String(36), index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    impact_method: Mapped[str] = mapped_column(String(200))
    requested_by: Mapped[str] = mapped_column(String(100))
    submitted_by: Mapped[str | None] = mapped_column(String(100))
    approved_by: Mapped[str | None] = mapped_column(String(100))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    engine: Mapped[str] = mapped_column(String(50))
    engine_version: Mapped[str | None] = mapped_column(String(100))
    raw_result_object_key: Mapped[str | None] = mapped_column(String(500))
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    manifest_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    summary: Mapped[ResultSummary | None] = relationship(back_populates="run", uselist=False)
    contributions: Mapped[list[ResultContribution]] = relationship(back_populates="run")


class ResultSummary(Base, TimestampMixin):
    __tablename__ = "result_summary"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("calculation_run.id"), unique=True)
    total_kg_co2e: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    functional_unit: Mapped[str] = mapped_column(String(300))
    boundary: Mapped[str] = mapped_column(String(100))
    impact_method: Mapped[str] = mapped_column(String(200))
    aircraft: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    biogenic_emissions: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    biogenic_removals: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    fossil: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    land_use_change: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    raw_materials: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    inbound_transport: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    manufacturing: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    packaging: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    data_quality_status: Mapped[str] = mapped_column(String(50))
    run: Mapped[CalculationRun] = relationship(back_populates="summary")


class ResultContribution(Base, TimestampMixin):
    __tablename__ = "result_contribution"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("calculation_run.id"), index=True)
    dimension: Mapped[str] = mapped_column(String(50))
    code: Mapped[str] = mapped_column(String(200))
    name: Mapped[str] = mapped_column(String(300))
    amount_kg_co2e: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    rank: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    run: Mapped[CalculationRun] = relationship(back_populates="contributions")


class EvidenceDocument(Base, TimestampMixin):
    __tablename__ = "evidence_document"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    object_type: Mapped[str] = mapped_column(String(100), index=True)
    object_id: Mapped[str] = mapped_column(String(36), index=True)
    document_type: Mapped[str] = mapped_column(String(100))
    object_key: Mapped[str] = mapped_column(String(500))
    sha256: Mapped[str] = mapped_column(String(64))
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class AuditEvent(Base):
    __tablename__ = "audit_event"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    actor: Mapped[str] = mapped_column(String(100), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    object_type: Mapped[str] = mapped_column(String(100), index=True)
    object_id: Mapped[str] = mapped_column(String(36), index=True)
    before_hash: Mapped[str | None] = mapped_column(String(64))
    after_hash: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class OutboxEvent(Base, TimestampMixin):
    __tablename__ = "outbox_event"
    __table_args__ = (
        UniqueConstraint("event_type", "aggregate_id", name="uq_outbox_event_aggregate"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    aggregate_type: Mapped[str] = mapped_column(String(100))
    aggregate_id: Mapped[str] = mapped_column(String(36), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
