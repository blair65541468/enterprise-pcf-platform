from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

RecordKind = Literal[
    "product",
    "bom",
    "factor",
    "route",
    "equipment",
    "supplier",
    "transport",
]


class ImportRecord(BaseModel):
    """Source-neutral normalized record accepted by the import application service."""

    model_config = ConfigDict(frozen=True)

    kind: RecordKind
    source_name: str
    source_row: int | None = None
    values: dict[str, Any] = Field(default_factory=dict)


class ImportFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    sha256: str
    content: bytes
    headers: tuple[str, ...]
    rows: tuple[dict[str, Any], ...]


class ImportBatch(BaseModel):
    """Transport-independent import command.

    A future FineReport adapter should produce this model instead of writing
    directly to SQLAlchemy models.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    source: str
    files: tuple[ImportFile, ...] = ()
    records: tuple[ImportRecord, ...] = ()
