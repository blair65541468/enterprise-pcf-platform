from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import record_audit
from app.auth import Principal, require_role
from app.db import get_db
from app.models import (
    EmissionFactor,
    FactorVersion,
    MappingStatus,
    Material,
    MaterialProcessMapping,
    ModelTemplate,
    ModelTemplateVersion,
    ProcessRoute,
    Product,
    ProductVersion,
    TransportActivity,
)
from app.schemas import FactorApproval, MappingCreate, ModelTemplateCreate, TransportCreate
from app.utils import hash_payload

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.post("/factors/{factor_code}/approve")
def approve_factor(
    factor_code: str,
    request: FactorApproval,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("lca_reviewer")),
):
    version = db.scalar(
        select(FactorVersion)
        .join(EmissionFactor)
        .where(EmissionFactor.factor_code == factor_code)
        .order_by(FactorVersion.version.desc())
    )
    if not version:
        raise HTTPException(status_code=404, detail="Factor not found")
    if version.approved:
        raise HTTPException(
            status_code=409,
            detail="Approved factor versions are immutable; import a new factor version",
        )
    version.density_kg_m3 = request.density_kg_m3 or version.density_kg_m3
    version.licence_ref = request.licence_ref or version.licence_ref
    version.content_hash = hash_payload(
        {
            "value": str(version.value),
            "activity_unit": version.activity_unit,
            "co2e_unit": version.co2e_unit,
            "source": version.source,
            "standard": version.standard,
            "region": version.region,
            "reference_year": version.reference_year,
            "data_quality": version.data_quality,
            "density_kg_m3": str(version.density_kg_m3) if version.density_kg_m3 else None,
            "licence_ref": version.licence_ref,
        }
    )
    version.approved = True
    record_audit(
        db,
        actor=principal.subject,
        action="factor.approved",
        object_type="factor_version",
        object_id=version.id,
        after_hash=hash_payload(
            {
                "value": str(version.value),
                "unit": version.activity_unit,
                "density": str(version.density_kg_m3) if version.density_kg_m3 else None,
            }
        ),
    )
    db.commit()
    return {"factor_code": factor_code, "version": version.version, "approved": True}


@router.post("/mappings/materials")
def create_material_mapping(
    request: MappingCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("lca_reviewer")),
):
    material = db.scalar(select(Material).where(Material.code == request.material_code))
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    mapping = MaterialProcessMapping(
        material_id=material.id,
        process_uuid=request.process_uuid,
        reference_flow_uuid=request.reference_flow_uuid,
        openlca_unit=request.openlca_unit,
        conversion_rule=request.conversion_rule,
        region=request.region,
        reference_year=request.reference_year,
        database_version=request.database_version,
        status=MappingStatus.approved,
        reviewed_by=principal.subject,
    )
    db.add(mapping)
    db.flush()
    record_audit(
        db,
        actor=principal.subject,
        action="material_mapping.approved",
        object_type="material_process_mapping",
        object_id=mapping.id,
        details=request.model_dump(mode="json"),
    )
    db.commit()
    return {"id": mapping.id, "status": mapping.status.value}


@router.post("/products/{sku}/transport-activities")
def create_transport(
    sku: str,
    request: TransportCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("lca_reviewer")),
):
    product_version = db.scalar(
        select(ProductVersion)
        .join(Product)
        .where(Product.sku == sku)
        .order_by(ProductVersion.version.desc())
    )
    factor_version = db.scalar(
        select(FactorVersion)
        .join(EmissionFactor)
        .where(EmissionFactor.factor_code == request.factor_code)
        .order_by(FactorVersion.version.desc())
    )
    if not product_version or not factor_version:
        raise HTTPException(status_code=404, detail="Product or factor not found")
    if not factor_version.approved:
        raise HTTPException(status_code=409, detail="Transport factor must be approved")
    activity = TransportActivity(
        product_version_id=product_version.id,
        mode=request.mode,
        distance_km=request.distance_km,
        mass_kg=request.mass_kg,
        load_factor=request.load_factor,
        factor_version_id=factor_version.id,
        source=request.source,
        approved=True,
    )
    db.add(activity)
    db.flush()
    record_audit(
        db,
        actor=principal.subject,
        action="transport_activity.approved",
        object_type="transport_activity",
        object_id=activity.id,
        details=request.model_dump(mode="json"),
    )
    db.commit()
    return {"id": activity.id, "approved": True}


@router.post("/products/{sku}/routes/{route_version}/approve")
def approve_route(
    sku: str,
    route_version: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("lca_reviewer")),
):
    route = db.scalar(
        select(ProcessRoute)
        .join(Product)
        .where(Product.sku == sku, ProcessRoute.version == route_version)
    )
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    route.approved = True
    record_audit(
        db,
        actor=principal.subject,
        action="route.approved",
        object_type="process_route",
        object_id=route.id,
        details={"sku": sku, "version": route_version},
    )
    db.commit()
    return {"id": route.id, "approved": True}


@router.post("/model-templates")
def create_model_template(
    request: ModelTemplateCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("lca_reviewer")),
):
    template = db.scalar(select(ModelTemplate).where(ModelTemplate.code == request.code))
    if not template:
        template = ModelTemplate(
            code=request.code,
            name=request.name,
            product_family=request.product_family,
        )
        db.add(template)
        db.flush()
    if db.scalar(
        select(ModelTemplateVersion).where(
            ModelTemplateVersion.template_id == template.id,
            ModelTemplateVersion.version == request.version,
        )
    ):
        raise HTTPException(status_code=409, detail="Template version already exists")
    version = ModelTemplateVersion(
        template_id=template.id,
        version=request.version,
        product_system_uuid=request.product_system_uuid,
        impact_method_uuid=request.impact_method_uuid,
        database_version=request.database_version,
        parameter_schema=request.parameter_schema,
        approved=True,
    )
    db.add(version)
    db.flush()
    record_audit(
        db,
        actor=principal.subject,
        action="model_template.approved",
        object_type="model_template_version",
        object_id=version.id,
        details=request.model_dump(mode="json"),
    )
    db.commit()
    return {"id": version.id, "version": version.version, "approved": True}
