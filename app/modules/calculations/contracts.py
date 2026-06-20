from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.snapshots.contracts import SnapshotPayload


class CalculationInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot: SnapshotPayload
    impact_method: str


class ModelTemplateConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    product_system_uuid: str
    impact_method_uuid: str
    database_version: str
    parameter_schema: dict[str, Any] = Field(default_factory=dict)
    parameter_contexts: dict[str, dict[str, Any]] = Field(default_factory=dict)
    stage_process_uuids: dict[str, list[str]] = Field(default_factory=dict)
