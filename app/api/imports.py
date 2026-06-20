from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth import Principal, require_role
from app.db import get_db
from app.models import ImportJob
from app.schemas import ImportJobOut
from app.services.import_service import ExcelImportService
from app.storage import get_storage

router = APIRouter(prefix="/v1/imports", tags=["imports"])


@router.post("/excel", response_model=ImportJobOut)
async def import_excel(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
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
        job = ExcelImportService(db, get_storage()).import_files(payloads, principal.subject)
        return db.scalar(
            select(ImportJob)
            .options(selectinload(ImportJob.issues))
            .where(ImportJob.id == job.id)
        )
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

