from __future__ import annotations

import enum
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.modules.model_base import TimestampMixin, new_id


class MappingStatus(str, enum.Enum):
    draft = "draft"
    approved = "approved"
    rejected = "rejected"


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
    status: Mapped[MappingStatus] = mapped_column(
        Enum(MappingStatus), default=MappingStatus.draft
    )
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
