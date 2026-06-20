from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SnapshotPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: int = Field(default=1, ge=1)
    sku: str
    product_name: str
    functional_unit: str
    boundary: str
    factor_set_version: str
    product_version: int
    route_version: str
    bom: list[dict[str, Any]]
    energy: list[dict[str, Any]]
    transport: list[dict[str, Any]]
    openlca_parameters: dict[str, str]
    stage_estimates: dict[str, str]

    @classmethod
    def load_compatible(cls, payload: dict[str, Any]) -> "SnapshotPayload":
        return cls.model_validate({"schema_version": 1, **payload})
