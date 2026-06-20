from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ImportStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    validated = "validated"
    failed = "failed"


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


class MappingStatus(str, enum.Enum):
    draft = "draft"
    approved = "approved"
    rejected = "rejected"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Product(Base, TimestampMixin):
    __tablename__ = "product"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    sku: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    brand_sku: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(300))
    target_market: Mapped[str | None] = mapped_column(String(100))
    versions: Mapped[list[ProductVersion]] = relationship(back_populates="product")


class ProductVersion(Base, TimestampMixin):
    __tablename__ = "product_version"
    __table_args__ = (UniqueConstraint("product_id", "version", name="uq_product_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    product_id: Mapped[str] = mapped_column(ForeignKey("product.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    source_import_id: Mapped[str | None] = mapped_column(ForeignKey("import_job.id"))
    payload: Mapped[dict] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    product: Mapped[Product] = relationship(back_populates="versions")
    bom_lines: Mapped[list[BomLine]] = relationship(back_populates="product_version")


class Material(Base, TimestampMixin):
    __tablename__ = "material"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(300))
    category: Mapped[str | None] = mapped_column(String(200))


class EmissionFactor(Base, TimestampMixin):
    __tablename__ = "emission_factor"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    factor_code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    material_code: Mapped[str | None] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(300))
    versions: Mapped[list[FactorVersion]] = relationship(back_populates="factor")


class FactorVersion(Base, TimestampMixin):
    __tablename__ = "factor_version"
    __table_args__ = (UniqueConstraint("factor_id", "version", name="uq_factor_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    factor_id: Mapped[str] = mapped_column(ForeignKey("emission_factor.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    value: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    activity_unit: Mapped[str] = mapped_column(String(50))
    co2e_unit: Mapped[str] = mapped_column(String(80))
    source: Mapped[str] = mapped_column(String(500))
    standard: Mapped[str | None] = mapped_column(String(200))
    region: Mapped[str | None] = mapped_column(String(100))
    reference_year: Mapped[int | None] = mapped_column(Integer)
    data_quality: Mapped[str | None] = mapped_column(String(100))
    density_kg_m3: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    licence_ref: Mapped[str | None] = mapped_column(String(500))
    content_hash: Mapped[str] = mapped_column(String(64))
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    factor: Mapped[EmissionFactor] = relationship(back_populates="versions")


class BomLine(Base, TimestampMixin):
    __tablename__ = "bom_line"
    __table_args__ = (UniqueConstraint("product_version_id", "line_no", name="uq_bom_line"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    product_version_id: Mapped[str] = mapped_column(ForeignKey("product_version.id"), index=True)
    line_no: Mapped[int] = mapped_column(Integer)
    material_id: Mapped[str] = mapped_column(ForeignKey("material.id"), index=True)
    part_name: Mapped[str] = mapped_column(String(300))
    material_type: Mapped[str | None] = mapped_column(String(100))
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    unit: Mapped[str] = mapped_column(String(50))
    weight_kg_each: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    factor_version_id: Mapped[str | None] = mapped_column(ForeignKey("factor_version.id"))
    stage: Mapped[str] = mapped_column(String(50), default="raw_materials")
    source_row: Mapped[int | None] = mapped_column(Integer)
    product_version: Mapped[ProductVersion] = relationship(back_populates="bom_lines")
    material: Mapped[Material] = relationship()
    factor_version: Mapped[FactorVersion | None] = relationship()


class Supplier(Base, TimestampMixin):
    __tablename__ = "supplier"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    supplier_code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(300))
    category: Mapped[str | None] = mapped_column(String(200))
    certifications: Mapped[str | None] = mapped_column(Text)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False)


class ProcessRoute(Base, TimestampMixin):
    __tablename__ = "process_route"
    __table_args__ = (UniqueConstraint("product_id", "version", name="uq_route_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    product_id: Mapped[str] = mapped_column(ForeignKey("product.id"), index=True)
    route_code: Mapped[str] = mapped_column(String(100))
    version: Mapped[str] = mapped_column(String(50))
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    steps: Mapped[list[RouteStep]] = relationship(back_populates="route")


class RouteStep(Base, TimestampMixin):
    __tablename__ = "route_step"
    __table_args__ = (UniqueConstraint("route_id", "sequence", name="uq_route_step"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    route_id: Mapped[str] = mapped_column(ForeignKey("process_route.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    process_code: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(300))
    standard_time_min: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    energy_kwh_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    route: Mapped[ProcessRoute] = relationship(back_populates="steps")


class Equipment(Base, TimestampMixin):
    __tablename__ = "equipment"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    equipment_code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(300))
    process_code: Mapped[str | None] = mapped_column(String(100))
    area: Mapped[str | None] = mapped_column(String(200))
    rated_power_kw: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    energy_type: Mapped[str | None] = mapped_column(String(100))
    allocation_pool: Mapped[str | None] = mapped_column(String(100))


class EnergyActivity(Base, TimestampMixin):
    __tablename__ = "energy_activity"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    product_version_id: Mapped[str] = mapped_column(ForeignKey("product_version.id"), index=True)
    route_step_id: Mapped[str | None] = mapped_column(ForeignKey("route_step.id"))
    energy_type: Mapped[str] = mapped_column(String(100))
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    unit: Mapped[str] = mapped_column(String(50))
    factor_version_id: Mapped[str | None] = mapped_column(ForeignKey("factor_version.id"))
    source: Mapped[str] = mapped_column(String(300))
    approved: Mapped[bool] = mapped_column(Boolean, default=False)


class TransportActivity(Base, TimestampMixin):
    __tablename__ = "transport_activity"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    product_version_id: Mapped[str] = mapped_column(ForeignKey("product_version.id"), index=True)
    material_id: Mapped[str | None] = mapped_column(ForeignKey("material.id"))
    supplier_id: Mapped[str | None] = mapped_column(ForeignKey("supplier.id"))
    mode: Mapped[str] = mapped_column(String(100))
    distance_km: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    mass_kg: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    load_factor: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    factor_version_id: Mapped[str | None] = mapped_column(ForeignKey("factor_version.id"))
    source: Mapped[str] = mapped_column(String(300))
    approved: Mapped[bool] = mapped_column(Boolean, default=False)


class MaterialProcessMapping(Base, TimestampMixin):
    __tablename__ = "material_process_mapping"
    __table_args__ = (
        UniqueConstraint("material_id", "database_version", name="uq_material_process_mapping"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    material_id: Mapped[str] = mapped_column(ForeignKey("material.id"), index=True)
    process_uuid: Mapped[str] = mapped_column(String(100))
    reference_flow_uuid: Mapped[str] = mapped_column(String(100))
    openlca_unit: Mapped[str] = mapped_column(String(50))
    conversion_rule: Mapped[dict] = mapped_column(JSON)
    region: Mapped[str | None] = mapped_column(String(100))
    reference_year: Mapped[int | None] = mapped_column(Integer)
    database_version: Mapped[str] = mapped_column(String(100))
    status: Mapped[MappingStatus] = mapped_column(Enum(MappingStatus), default=MappingStatus.draft)
    reviewed_by: Mapped[str | None] = mapped_column(String(100))


class ModelTemplate(Base, TimestampMixin):
    __tablename__ = "model_template"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(300))
    product_family: Mapped[str] = mapped_column(String(200))
    versions: Mapped[list[ModelTemplateVersion]] = relationship(back_populates="template")


class ModelTemplateVersion(Base, TimestampMixin):
    __tablename__ = "model_template_version"
    __table_args__ = (UniqueConstraint("template_id", "version", name="uq_template_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    template_id: Mapped[str] = mapped_column(ForeignKey("model_template.id"), index=True)
    version: Mapped[str] = mapped_column(String(100))
    product_system_uuid: Mapped[str] = mapped_column(String(100))
    impact_method_uuid: Mapped[str] = mapped_column(String(100))
    database_version: Mapped[str] = mapped_column(String(100))
    parameter_schema: Mapped[dict] = mapped_column(JSON)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    template: Mapped[ModelTemplate] = relationship(back_populates="versions")


class ImportJob(Base, TimestampMixin):
    __tablename__ = "import_job"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    status: Mapped[ImportStatus] = mapped_column(Enum(ImportStatus), default=ImportStatus.uploaded)
    created_by: Mapped[str] = mapped_column(String(100))
    file_manifest: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    issues: Mapped[list[ImportIssue]] = relationship(back_populates="import_job")


class ImportIssue(Base, TimestampMixin):
    __tablename__ = "import_issue"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    import_job_id: Mapped[str] = mapped_column(ForeignKey("import_job.id"), index=True)
    severity: Mapped[str] = mapped_column(String(20))
    file_name: Mapped[str] = mapped_column(String(300))
    row_number: Mapped[int | None] = mapped_column(Integer)
    field: Mapped[str | None] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)
    import_job: Mapped[ImportJob] = relationship(back_populates="issues")


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
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("calculation_snapshot.id"), index=True)
    model_template_version_id: Mapped[str] = mapped_column(ForeignKey("model_template_version.id"))
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True)
    status: Mapped[CalculationStatus] = mapped_column(
        Enum(CalculationStatus), default=CalculationStatus.draft, index=True
    )
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
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(100), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    object_type: Mapped[str] = mapped_column(String(100), index=True)
    object_id: Mapped[str] = mapped_column(String(36), index=True)
    before_hash: Mapped[str | None] = mapped_column(String(64))
    after_hash: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict] = mapped_column(JSON, default=dict)

