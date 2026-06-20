from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    BomLine,
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
    RouteStep,
    TransportActivity,
)
from app.utils import hash_payload


def seed_valid_pilot(db: Session):
    product = Product(sku="INT-WD-001", brand_sku="BRD-WARDROBE", name="Test Wardrobe", target_market="EU")
    db.add(product)
    db.flush()
    pv = ProductVersion(
        product_id=product.id,
        version=1,
        payload={"sku": product.sku},
        content_hash=hash_payload({"sku": product.sku}),
    )
    db.add(pv)
    db.flush()

    raw = Material(code="RM-WD-001", name="Particle board", category="wood")
    package = Material(code="RM-PK-001", name="Carton", category="packaging")
    db.add_all([raw, package])
    db.flush()

    def factor(code, material_code, name, value, unit):
        entity = EmissionFactor(factor_code=code, material_code=material_code, name=name)
        db.add(entity)
        db.flush()
        version = FactorVersion(
            factor_id=entity.id,
            version=1,
            value=Decimal(value),
            activity_unit=unit,
            co2e_unit=f"kgCO2e/{unit}",
            source="test approved source",
            standard="ISO 14067",
            region="CN",
            reference_year=2025,
            data_quality="test",
            content_hash=hash_payload({"code": code, "value": value, "unit": unit}),
            approved=True,
        )
        db.add(version)
        db.flush()
        return version

    raw_factor = factor("CF-WD-001", raw.code, "Particle board", "3", "kg")
    pack_factor = factor("CF-PK-001", package.code, "Carton", "2", "kg")
    grid_factor = factor("CF-ENERGY-GRID", None, "Grid Electricity South China", "0.5", "kWh")
    truck_factor = factor("CF-TRANSPORT-TRUCK", None, "Heavy Duty Diesel Truck", "0.1", "t·km")

    db.add_all(
        [
            BomLine(
                product_version_id=pv.id,
                line_no=1,
                material_id=raw.id,
                part_name="Board",
                material_type="Raw material",
                quantity=Decimal("1"),
                unit="pcs",
                weight_kg_each=Decimal("2"),
                factor_version_id=raw_factor.id,
                stage="raw_materials",
            ),
            BomLine(
                product_version_id=pv.id,
                line_no=2,
                material_id=package.id,
                part_name="Carton",
                material_type="Packaging",
                quantity=Decimal("1"),
                unit="pcs",
                weight_kg_each=Decimal("0.5"),
                factor_version_id=pack_factor.id,
                stage="packaging",
            ),
        ]
    )
    for material, unit in ((raw, "kg"), (package, "kg")):
        db.add(
            MaterialProcessMapping(
                material_id=material.id,
                process_uuid=f"process-{material.code}",
                reference_flow_uuid=f"flow-{material.code}",
                openlca_unit=unit,
                conversion_rule={"type": "identity"},
                region="CN",
                reference_year=2025,
                database_version="test-db-v1",
                status=MappingStatus.approved,
                reviewed_by="reviewer",
            )
        )

    route = ProcessRoute(
        product_id=product.id,
        route_code="WARDROBE-GATE",
        version="WD-ROUTE-V1",
        approved=True,
    )
    db.add(route)
    db.flush()
    db.add(
        RouteStep(
            route_id=route.id,
            sequence=1,
            process_code="PROC-01",
            name="Manufacturing",
            standard_time_min=Decimal("10"),
            energy_kwh_per_unit=Decimal("1"),
        )
    )
    db.add(
        TransportActivity(
            product_version_id=pv.id,
            mode="Heavy Duty Diesel Truck",
            distance_km=Decimal("100"),
            mass_kg=Decimal("2.5"),
            load_factor=Decimal("0.8"),
            factor_version_id=truck_factor.id,
            source="test route",
            approved=True,
        )
    )
    template = ModelTemplate(code="WARDROBE-GATE", name="Wardrobe", product_family="wardrobe")
    db.add(template)
    db.flush()
    db.add(
        ModelTemplateVersion(
            template_id=template.id,
            version="WARDROBE-GATE-V1",
            product_system_uuid="mock-product-system",
            impact_method_uuid="mock-impact-method",
            database_version="test-db-v1",
            parameter_schema={},
            approved=True,
        )
    )
    db.commit()
    return product, pv, raw_factor, pack_factor, grid_factor, truck_factor

