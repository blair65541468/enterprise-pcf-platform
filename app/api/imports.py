from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.audit import record_audit
from app.auth import Principal, require_role
from app.core.db import SessionLocal, UnitOfWork
from app.core.dependencies import object_storage
from app.db import get_db
from app.models import ImportJob, ImportStatus
from app.modules.imports.schemas import ImportJobOut
from app.services.import_service import ExcelImportService, ImportProcessingError
from app.storage import ObjectStorage

router = APIRouter(prefix="/v1/imports", tags=["imports"])


@router.post("/excel", response_model=ImportJobOut)
async def import_excel(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(object_storage),
    principal: Principal = Depends(require_role("data_submitter")),
):
    if not files:
        raise HTTPException(status_code=400, detail="At least one XLSX file is required")
    payloads = []
    for file in files:
        if not file.filename or not file.filename.lower().endswith(".xlsx"):
            raise HTTPException(status_code=400, detail=f"Unsupported file: {file.filename}")
        payloads.append((file.filename, await file.read()))
    try:
        job = ExcelImportService(db, storage).import_files(payloads, principal.subject)
        return db.scalar(
            select(ImportJob)
            .options(selectinload(ImportJob.issues))
            .where(ImportJob.id == job.id)
        )
    except ImportProcessingError as exc:
        db.rollback()
        with SessionLocal() as failure_db, UnitOfWork(failure_db):
            failed = ImportJob(
                id=exc.job_id,
                status=ImportStatus.failed,
                created_by=exc.actor,
                file_manifest=exc.manifest,
                summary={"error": str(exc.cause)},
                completed_at=datetime.now(timezone.utc),
            )
            failure_db.add(failed)
            record_audit(
                failure_db,
                actor=exc.actor,
                action="import.failed",
                object_type="import_job",
                object_id=exc.job_id,
                details={"error": str(exc.cause)},
            )
        raise HTTPException(status_code=422, detail=str(exc.cause)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{import_id}", response_model=ImportJobOut)
def get_import(import_id: str, db: Session = Depends(get_db)):
    job = db.scalar(
        select(ImportJob)
        .options(selectinload(ImportJob.issues))
        .where(ImportJob.id == import_id)
    )
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    return job
