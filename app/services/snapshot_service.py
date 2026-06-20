from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.audit import record_audit
from app.models import (
    BomLine,
    CalculationSnapshot,
    EmissionFactor,
    EnergyActivity,
    FactorVersion,
    MappingStatus,
    MaterialProcessMapping,
    ProcessRoute,
    Product,
    ProductVersion,
    RouteStep,
    TransportActivity,
)
from app.modules.catalog.units import UnitConversionError, convert_activity_amount
from app.modules.snapshots.contracts import SnapshotPayload
from app.utils import hash_payload


class SnapshotValidationError(ValueError):
    def __init__(self, errors: list[dict]):
        super().__init__("Snapshot validation failed")
        self.errors = errors


class SnapshotService:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        sku: str,
        factor_set_version: str,
        route_version: str,
        boundary: str,
        actor: str,
    ) -> CalculationSnapshot:
        product = self.db.scalar(select(Product).where(Product.sku == sku))
        if not product:
            raise ValueError(f"Unknown product: {sku}")
        product_version = self.db.scalar(
            select(ProductVersion)
            .where(ProductVersion.product_id == product.id)
            .order_by(ProductVersion.version.desc())
        )
        route = self.db.scalar(
            select(ProcessRoute)
            .options(selectinload(ProcessRoute.steps))
            .where(ProcessRoute.product_id == product.id, ProcessRoute.version == route_version)
        )
        bom_lines = list(
            self.db.scalars(
                select(BomLine)
                .options(
                    selectinload(BomLine.material),
                    selectinload(BomLine.factor_version).selectinload(FactorVersion.factor),
                )
                .where(BomLine.product_version_id == product_version.id)
                .order_by(BomLine.line_no)
            )
        )
        errors: list[dict] = []
        if not bom_lines:
            errors.append({"code": "BOM_MISSING", "message": "Product has no BOM lines"})
        if not route:
            errors.append({"code": "ROUTE_MISSING", "message": f"Route {route_version} not found"})
        elif not route.approved:
            errors.append({"code": "ROUTE_NOT_APPROVED", "message": f"Route {route_version} is not approved"})

        bom_payload = []
        stage_estimates = {
            "raw_materials": Decimal("0"),
            "inbound_transport": Decimal("0"),
            "manufacturing": Decimal("0"),
            "packaging": Decimal("0"),
        }
        openlca_parameters: dict[str, str] = {}
        for line in bom_lines:
            factor = line.factor_version
            if factor is None:
                errors.append(
                    {"code": "FACTOR_MISSING", "line": line.line_no, "material": line.material.code}
                )
                continue
            if not factor.approved:
                errors.append(
                    {"code": "FACTOR_NOT_APPROVED", "line": line.line_no, "factor": factor.factor.factor_code}
                )
            if line.weight_kg_each is None:
                errors.append({"code": "BOM_WEIGHT_MISSING", "line": line.line_no})
                continue
            mass_kg = Decimal(line.quantity) * Decimal(line.weight_kg_each)
            try:
                activity_amount = convert_activity_amount(
                    quantity=Decimal(line.quantity),
                    weight_kg_each=Decimal(line.weight_kg_each),
                    activity_unit=factor.activity_unit,
                    density_kg_m3=(
                        Decimal(factor.density_kg_m3) if factor.density_kg_m3 else None
                    ),
                )
            except UnitConversionError:
                code = (
                    "DENSITY_MISSING"
                    if factor.activity_unit.lower() in {"m³", "m3"}
                    else "UNIT_CONVERSION_MISSING"
                )
                errors.append(
                    {
                        "code": code,
                        "line": line.line_no,
                        "from": line.unit,
                        "to": factor.activity_unit,
                        "material": line.material.code,
                    }
                )
                continue
            mapping = self.db.scalar(
                select(MaterialProcessMapping)
                .where(
                    MaterialProcessMapping.material_id == line.material_id,
                    MaterialProcessMapping.status == MappingStatus.approved,
                )
                .order_by(MaterialProcessMapping.created_at.desc())
            )
            if not mapping:
                errors.append(
                    {
                        "code": "OPENLCA_MAPPING_MISSING",
                        "line": line.line_no,
                        "material": line.material.code,
                    }
                )
            contribution = activity_amount * Decimal(factor.value)
            stage_estimates[line.stage] += contribution
            parameter_name = f"mat_{line.material.code.lower().replace('-', '_')}"
            openlca_parameters[parameter_name] = str(activity_amount)
            bom_payload.append(
                {
                    "line_no": line.line_no,
                    "material_code": line.material.code,
                    "part_name": line.part_name,
                    "stage": line.stage,
                    "quantity": str(line.quantity),
                    "unit": line.unit,
                    "weight_kg_each": str(line.weight_kg_each),
                    "mass_kg": str(mass_kg),
                    "factor_code": factor.factor.factor_code,
                    "factor_version": factor.version,
                    "factor_value": str(factor.value),
                    "factor_activity_unit": factor.activity_unit,
                    "factor_source": factor.source,
                    "activity_amount": str(activity_amount),
                    "mapping": {
                        "process_uuid": mapping.process_uuid,
                        "reference_flow_uuid": mapping.reference_flow_uuid,
                        "openlca_unit": mapping.openlca_unit,
                        "database_version": mapping.database_version,
                    }
                    if mapping
                    else None,
                }
            )

        energy_payload = self._energy_payload(product_version, route, errors, stage_estimates, openlca_parameters)
        transport_payload = self._transport_payload(product_version, errors, stage_estimates, openlca_parameters)
        payload_model = SnapshotPayload(
            schema_version=1,
            sku=product.sku,
            product_name=product.name,
            functional_unit=f"1 completed and packaged {product.name} at factory gate",
            boundary=boundary,
            factor_set_version=factor_set_version,
            product_version=product_version.version,
            route_version=route_version,
            bom=bom_payload,
            energy=energy_payload,
            transport=transport_payload,
            openlca_parameters=openlca_parameters,
            stage_estimates={key: str(value) for key, value in stage_estimates.items()},
        )
        payload = payload_model.model_dump(mode="json")
        if errors:
            raise SnapshotValidationError(errors)
        version = int(
            self.db.scalar(
                select(func.max(CalculationSnapshot.version)).where(
                    CalculationSnapshot.product_id == product.id
                )
            )
            or 0
        ) + 1
        snapshot = CalculationSnapshot(
            product_id=product.id,
            version=version,
            product_version_id=product_version.id,
            route_id=route.id,
            factor_set_version=factor_set_version,
            boundary=boundary,
            payload=payload,
            manifest_hash=hash_payload(payload),
            validation_errors=[],
            created_by=actor,
        )
        self.db.add(snapshot)
        self.db.flush()
        record_audit(
            self.db,
            actor=actor,
            action="snapshot.created",
            object_type="calculation_snapshot",
            object_id=snapshot.id,
            after_hash=snapshot.manifest_hash,
            details={"sku": sku, "version": version},
        )
        self.db.flush()
        return snapshot

    def _energy_payload(
        self,
        product_version: ProductVersion,
        route: ProcessRoute | None,
        errors: list[dict],
        stage_estimates: dict[str, Decimal],
        openlca_parameters: dict[str, str],
    ) -> list[dict]:
        activities = list(
            self.db.scalars(
                select(EnergyActivity).where(EnergyActivity.product_version_id == product_version.id)
            )
        )
        payload = []
        if activities:
            source_items = activities
        else:
            if not route:
                return []
            grid_factor = self.db.scalar(
                select(FactorVersion)
                .join(EmissionFactor)
                .where(
                    FactorVersion.approved.is_(True),
                    EmissionFactor.name.ilike("%Grid Electricity%"),
                )
                .order_by(FactorVersion.version.desc())
            ) or self.db.scalar(
                select(FactorVersion)
                .join(EmissionFactor)
                .where(
                    FactorVersion.approved.is_(True),
                    EmissionFactor.name.ilike("%市电%"),
                )
                .order_by(FactorVersion.version.desc())
            )
            if not grid_factor:
                errors.append({"code": "GRID_FACTOR_MISSING", "message": "Approved grid factor is required"})
                return []
            source_items = [
                {
                    "process_code": step.process_code,
                    "name": step.name,
                    "amount": step.energy_kwh_per_unit or Decimal("0"),
                    "unit": "kWh",
                    "factor": grid_factor,
                    "source": "approved route standard",
                }
                for step in sorted(route.steps, key=lambda x: x.sequence)
            ]
        for item in source_items:
            if isinstance(item, dict):
                factor = item["factor"]
                process_code = item["process_code"]
                name = item["name"]
                amount = Decimal(item["amount"])
                source = item["source"]
            else:
                factor = self.db.get(FactorVersion, item.factor_version_id)
                step = self.db.get(RouteStep, item.route_step_id) if item.route_step_id else None
                process_code = step.process_code if step else "ENERGY"
                name = step.name if step else item.energy_type
                amount = Decimal(item.amount)
                source = item.source
                if not item.approved:
                    errors.append({"code": "ENERGY_ACTIVITY_NOT_APPROVED", "id": item.id})
            if not factor or not factor.approved:
                errors.append({"code": "ENERGY_FACTOR_NOT_APPROVED", "process": process_code})
                continue
            contribution = amount * Decimal(factor.value)
            stage_estimates["manufacturing"] += contribution
            parameter_name = f"energy_{process_code.lower().replace('-', '_')}"
            openlca_parameters[parameter_name] = str(amount)
            payload.append(
                {
                    "process_code": process_code,
                    "name": name,
                    "amount": str(amount),
                    "unit": "kWh",
                    "factor_code": factor.factor.factor_code,
                    "factor_value": str(factor.value),
                    "source": source,
                }
            )
        return payload

    def _transport_payload(
        self,
        product_version: ProductVersion,
        errors: list[dict],
        stage_estimates: dict[str, Decimal],
        openlca_parameters: dict[str, str],
    ) -> list[dict]:
        activities = list(
            self.db.scalars(
                select(TransportActivity).where(
                    TransportActivity.product_version_id == product_version.id
                )
            )
        )
        if not activities:
            errors.append(
                {
                    "code": "INBOUND_TRANSPORT_MISSING",
                    "message": "At least one approved inbound transport activity is required",
                }
            )
            return []
        payload = []
        for index, item in enumerate(activities, start=1):
            factor = self.db.get(FactorVersion, item.factor_version_id)
            if not item.approved:
                errors.append({"code": "TRANSPORT_NOT_APPROVED", "id": item.id})
            if not factor or not factor.approved:
                errors.append({"code": "TRANSPORT_FACTOR_NOT_APPROVED", "id": item.id})
                continue
            tkm = Decimal(item.mass_kg) / Decimal("1000") * Decimal(item.distance_km)
            stage_estimates["inbound_transport"] += tkm * Decimal(factor.value)
            openlca_parameters[f"transport_{index}_tkm"] = str(tkm)
            payload.append(
                {
                    "mode": item.mode,
                    "distance_km": str(item.distance_km),
                    "mass_kg": str(item.mass_kg),
                    "load_factor": str(item.load_factor) if item.load_factor else None,
                    "factor_code": factor.factor.factor_code,
                    "factor_value": str(factor.value),
                    "material_code": None,
                    "source": item.source,
                }
            )
        return payload
