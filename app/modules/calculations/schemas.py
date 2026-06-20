from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.calculations.models import CalculationStatus
from app.modules.schema_base import ORMModel


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
