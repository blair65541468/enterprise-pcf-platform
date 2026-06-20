from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import Principal, require_role
from app.db import get_db
from app.schemas import SnapshotCreate, SnapshotOut
from app.services.snapshot_service import SnapshotService, SnapshotValidationError

router = APIRouter(prefix="/v1/products", tags=["products"])


@router.post("/{sku}/snapshots", response_model=SnapshotOut)
def create_snapshot(
    sku: str,
    request: SnapshotCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("data_submitter")),
):
    try:
        return SnapshotService(db).create(
            sku=sku,
            factor_set_version=request.factor_set_version,
            route_version=request.route_version,
            boundary=request.boundary,
            actor=principal.subject,
        )
    except SnapshotValidationError as exc:
        raise HTTPException(status_code=422, detail={"code": "SNAPSHOT_INVALID", "errors": exc.errors}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

