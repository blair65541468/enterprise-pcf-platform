from datetime import datetime

from pydantic import BaseModel

from app.modules.schema_base import ORMModel


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
