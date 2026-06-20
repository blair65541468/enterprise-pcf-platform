from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import CalculationStatus, ImportStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ImportIssueOut(ORMModel):
    severity: str
    file_name: str
    row_number: int | None
    field: str | None
    code: str
    message: str


class ImportJobOut(ORMModel):
    id: str
    status: ImportStatus
    file_manifest: list
    summary: dict
    created_at: datetime
    completed_at: datetime | None
    issues: list[ImportIssueOut] = []


class SnapshotCreate(BaseModel):
    factor_set_version: str = "2026.06"
    route_version: str = "WD-ROUTE-V1"
    boundary: str = "cradle_to_gate_with_packaging"


class SnapshotOut(ORMModel):
    id: str
    version: int
    factor_set_version: str
    boundary: str
    manifest_hash: str
    validation_errors: list
    created_at: datetime


class CalculationCreate(BaseModel):
    sku: str = "INT-WD-001"
    snapshot_version: int
    model_template_version: str = "WARDROBE-GATE-V1"
    factor_set_version: str = "2026.06"
    route_version: str = "WD-ROUTE-V1"
    impact_method: str = "IPCC-2021-ISO14067-GWP100"
    boundary: str = "cradle_to_gate_with_packaging"
    idempotency_key: str = Field(min_length=5, max_length=200)


class ResultSummaryOut(ORMModel):
    total_kg_co2e: Decimal
    functional_unit: str
    boundary: str
    impact_method: str
    aircraft: Decimal
    biogenic_emissions: Decimal
    biogenic_removals: Decimal
    fossil: Decimal
    land_use_change: Decimal
    raw_materials: Decimal
    inbound_transport: Decimal
    manufacturing: Decimal
    packaging: Decimal
    data_quality_status: str


class CalculationOut(ORMModel):
    id: str
    status: CalculationStatus
    idempotency_key: str
    impact_method: str
    engine: str
    error: str | None
    manifest_hash: str | None
    created_at: datetime
    summary: ResultSummaryOut | None = None


class ContributionOut(ORMModel):
    dimension: str
    code: str
    name: str
    amount_kg_co2e: Decimal
    rank: int | None
    metadata_json: dict


class RejectionRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=2000)


class DensityUpdate(BaseModel):
    density_kg_m3: Decimal = Field(gt=0)
    licence_ref: str | None = None


class MappingCreate(BaseModel):
    material_code: str
    process_uuid: str
    reference_flow_uuid: str
    openlca_unit: str
    conversion_rule: dict
    region: str | None = None
    reference_year: int | None = None
    database_version: str


class FactorApproval(BaseModel):
    density_kg_m3: Decimal | None = Field(default=None, gt=0)
    licence_ref: str | None = None


class TransportCreate(BaseModel):
    mode: str
    distance_km: Decimal = Field(gt=0)
    mass_kg: Decimal = Field(gt=0)
    load_factor: Decimal | None = Field(default=None, gt=0, le=1)
    factor_code: str
    source: str


class ModelTemplateCreate(BaseModel):
    code: str = "WARDROBE-GATE"
    name: str = "Board wardrobe cradle-to-gate PCF"
    product_family: str = "wardrobe"
    version: str = "WARDROBE-GATE-V1"
    product_system_uuid: str
    impact_method_uuid: str
    database_version: str
    parameter_schema: dict = Field(default_factory=dict)
