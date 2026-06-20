from decimal import Decimal

from pydantic import BaseModel, Field


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
