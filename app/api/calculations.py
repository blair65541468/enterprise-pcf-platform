from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth import Principal, require_role
from app.core.clock import Clock
from app.core.db import UnitOfWork
from app.core.dependencies import clock
from app.core.request_context import request_id_var
from app.db import get_db
from app.models import AuditEvent, CalculationRun, CalculationSnapshot, Product
from app.modules.calculations.schemas import (
    CalculationCreate,
    CalculationOut,
    ContributionOut,
    RejectionRequest,
)
from app.services.approval_service import ApprovalService
from app.services.calculation_service import CalculationService
from app.services.export_service import ExportService
from app.tasks import dispatch_outbox
from app.utils import hash_payload

router = APIRouter(prefix="/v1/calculations", tags=["calculations"])


def _load_run(db: Session, run_id: str) -> CalculationRun:
    db.expire_all()
    run = db.scalar(
        select(CalculationRun)
        .options(selectinload(CalculationRun.summary), selectinload(CalculationRun.contributions))
        .where(CalculationRun.id == run_id)
    )
    if not run:
        raise HTTPException(status_code=404, detail="Calculation not found")
    return run


@router.post("", response_model=CalculationOut)
def create_calculation(
    request: CalculationCreate,
    db: Session = Depends(get_db),
    application_clock: Clock = Depends(clock),
    principal: Principal = Depends(require_role("data_submitter")),
):
    product = db.scalar(select(Product).where(Product.sku == request.sku))
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    snapshot = db.scalar(
        select(CalculationSnapshot).where(
            CalculationSnapshot.product_id == product.id,
            CalculationSnapshot.version == request.snapshot_version,
        )
    )
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    if snapshot.factor_set_version != request.factor_set_version:
        raise HTTPException(status_code=409, detail="Factor set does not match frozen snapshot")
    if snapshot.payload.get("route_version") != request.route_version:
        raise HTTPException(status_code=409, detail="Route version does not match frozen snapshot")
    if snapshot.boundary != request.boundary:
        raise HTTPException(status_code=409, detail="Boundary does not match frozen snapshot")
    try:
        with UnitOfWork(db) as uow:
            run, created = CalculationService(db, clock=application_clock).create_run(
                snapshot=snapshot,
                template_version=request.model_template_version,
                impact_method=request.impact_method,
                idempotency_key=request.idempotency_key,
                request_hash=hash_payload(request.model_dump(mode="json")),
                actor=principal.subject,
                request_id=request_id_var.get(),
            )
            uow.commit()
        if created:
            dispatch_outbox.delay()
        return _load_run(db, run.id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{run_id}", response_model=CalculationOut)
def get_calculation(run_id: str, db: Session = Depends(get_db)):
    return _load_run(db, run_id)


@router.get("/{run_id}/contributions", response_model=list[ContributionOut])
def get_contributions(run_id: str, db: Session = Depends(get_db)):
    return _load_run(db, run_id).contributions


@router.post("/{run_id}/submit", response_model=CalculationOut)
def submit(
    run_id: str,
    db: Session = Depends(get_db),
    application_clock: Clock = Depends(clock),
    principal: Principal = Depends(require_role("data_submitter")),
):
    try:
        return ApprovalService(db, clock=application_clock).submit(
            _load_run(db, run_id), principal.subject
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{run_id}/approve", response_model=CalculationOut)
def approve(
    run_id: str,
    db: Session = Depends(get_db),
    application_clock: Clock = Depends(clock),
    principal: Principal = Depends(require_role("lca_reviewer")),
):
    try:
        return ApprovalService(db, clock=application_clock).approve(
            _load_run(db, run_id), principal.subject
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{run_id}/reject", response_model=CalculationOut)
def reject(
    run_id: str,
    request: RejectionRequest,
    db: Session = Depends(get_db),
    application_clock: Clock = Depends(clock),
    principal: Principal = Depends(require_role("lca_reviewer")),
):
    try:
        return ApprovalService(db, clock=application_clock).reject(
            _load_run(db, run_id), principal.subject, request.reason
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{run_id}/export.json")
def export_json(run_id: str, db: Session = Depends(get_db)):
    try:
        return Response(
            ExportService(db).as_json(run_id),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="pcf-{run_id}.json"'},
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{run_id}/export.xlsx")
def export_excel(run_id: str, db: Session = Depends(get_db)):
    try:
        return Response(
            ExportService(db).as_excel(run_id),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="pcf-{run_id}.xlsx"'},
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{run_id}/audit-events")
def get_audit_events(run_id: str, db: Session = Depends(get_db)):
    _load_run(db, run_id)
    events = db.scalars(
        select(AuditEvent).where(AuditEvent.object_id == run_id).order_by(AuditEvent.occurred_at)
    )
    return [
        {
            "id": event.id,
            "occurred_at": event.occurred_at,
            "actor": event.actor,
            "action": event.action,
            "before_hash": event.before_hash,
            "after_hash": event.after_hash,
            "details": event.details,
        }
        for event in events
    ]
