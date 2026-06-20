from datetime import datetime

from app.modules.imports.models import ImportStatus
from app.modules.schema_base import ORMModel


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
