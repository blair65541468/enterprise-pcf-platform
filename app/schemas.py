"""Backward-compatible aggregate of modular Pydantic schemas."""

from app.modules.calculations.schemas import (
    CalculationCreate,
    CalculationOut,
    ContributionOut,
    RejectionRequest,
    ResultSummaryOut,
)
from app.modules.catalog.schemas import (
    DensityUpdate,
    FactorApproval,
    MappingCreate,
    ModelTemplateCreate,
    TransportCreate,
)
from app.modules.imports.schemas import ImportIssueOut, ImportJobOut
from app.modules.schema_base import ORMModel
from app.modules.snapshots.schemas import SnapshotCreate, SnapshotOut

__all__ = [
    "CalculationCreate",
    "CalculationOut",
    "ContributionOut",
    "DensityUpdate",
    "FactorApproval",
    "ImportIssueOut",
    "ImportJobOut",
    "MappingCreate",
    "ModelTemplateCreate",
    "ORMModel",
    "RejectionRequest",
    "ResultSummaryOut",
    "SnapshotCreate",
    "SnapshotOut",
    "TransportCreate",
]
