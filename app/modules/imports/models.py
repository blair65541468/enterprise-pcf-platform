from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.modules.model_base import TimestampMixin, new_id


class ImportStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    validated = "validated"
    failed = "failed"


class ImportJob(Base, TimestampMixin):
    __tablename__ = "import_job"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    status: Mapped[ImportStatus] = mapped_column(Enum(ImportStatus), default=ImportStatus.uploaded)
    created_by: Mapped[str] = mapped_column(String(100))
    file_manifest: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    issues: Mapped[list[ImportIssue]] = relationship(back_populates="import_job")


class ImportIssue(Base, TimestampMixin):
    __tablename__ = "import_issue"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    import_job_id: Mapped[str] = mapped_column(ForeignKey("import_job.id"), index=True)
    severity: Mapped[str] = mapped_column(String(20))
    file_name: Mapped[str] = mapped_column(String(300))
    row_number: Mapped[int | None] = mapped_column(Integer)
    field: Mapped[str | None] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)
    import_job: Mapped[ImportJob] = relationship(back_populates="issues")
