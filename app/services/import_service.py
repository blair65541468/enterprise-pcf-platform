from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import record_audit
from app.core.metrics import IMPORTS
from app.models import (
    BomLine,
    EmissionFactor,
    Equipment,
    FactorVersion,
    ImportIssue,
    ImportJob,
    ImportStatus,
    Material,
    ProcessRoute,
    Product,
    ProductVersion,
    RouteStep,
    Supplier,
)
from app.modules.imports.excel import ExcelImportAdapter
from app.storage import ObjectStorage
from app.utils import as_decimal, hash_payload, json_safe, sha256_bytes


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _header(headers: list[str], needle: str, required: bool = True) -> str | None:
    found = next((h for h in headers if h == needle), None)
    if found is None:
        found = next((h for h in headers if needle.lower() in h.lower()), None)
    if required and not found:
        raise ValueError(f"Required column not found: {needle}")
    return found


def _issue(
    db: Session,
    job: ImportJob,
    severity: str,
    file_name: str,
    code: str,
    message: str,
    row_number: int | None = None,
    field: str | None = None,
) -> None:
    db.add(
        ImportIssue(
            import_job_id=job.id,
            severity=severity,
            file_name=file_name,
            row_number=row_number,
            field=field,
            code=code,
            message=message,
        )
    )


def _next_version(db: Session, model, parent_field, parent_id: str) -> int:
    current = db.scalar(select(func.max(model.version)).where(parent_field == parent_id))
    return int(current or 0) + 1


def _factor_code(material_code: str) -> str:
    return f"CF{material_code[2:]}" if material_code.startswith("RM") else f"CF-{material_code}"


class ImportProcessingError(RuntimeError):
    def __init__(
        self,
        *,
        job_id: str,
        actor: str,
        manifest: list[dict[str, Any]],
        cause: Exception,
    ):
        super().__init__(str(cause))
        self.job_id = job_id
        self.actor = actor
        self.manifest = manifest
        self.cause = cause


class ExcelImportService:
    def __init__(
        self,
        db: Session,
        storage: ObjectStorage,
        adapter: ExcelImportAdapter | None = None,
    ):
        self.db = db
        self.storage = storage
        self.adapter = adapter or ExcelImportAdapter()

    def import_files(self, files: list[tuple[str, bytes]], actor: str) -> ImportJob:
        manifest = []
        job = ImportJob(status=ImportStatus.processing, created_by=actor, file_manifest=[])
        self.db.add(job)
        self.db.flush()

        parsed: list[tuple[str, bytes, list[str], list[dict[str, Any]]]] = []
        batch = self.adapter.parse(files)
        for item in batch.files:
            key = f"imports/{job.id}/{item.sha256}-{Path(item.name).name}"
            self.storage.put(
                key,
                item.content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            if sha256_bytes(self.storage.get(key)) != item.sha256:
                raise RuntimeError(f"Stored import failed SHA-256 verification: {item.name}")
            headers = list(item.headers)
            rows = list(item.rows)
            parsed.append((item.name, item.content, headers, rows))
            manifest.append(
                {
                    "file_name": item.name,
                    "sha256": item.sha256,
                    "object_key": key,
                    "rows": len(rows),
                }
            )
            duplicates = [
                key
                for key, count in Counter(
                    header.split("__")[0] for header in headers
                ).items()
                if key and count > 1
            ]
            if duplicates:
                _issue(
                    self.db,
                    job,
                    "warning",
                    item.name,
                    "DUPLICATE_HEADERS",
                    f"Duplicate headers were renamed during import: {duplicates}",
                )
        job.file_manifest = manifest

        counts = Counter()
        try:
            # Dependency order: factors/products first, then BOM and operational data.
            for item in parsed:
                if self._is_factor_file(item[0]):
                    counts.update(self._import_factors(job, *item[0:1], item[2], item[3]))
            for item in parsed:
                if "Product_Master" in item[0]:
                    counts.update(self._import_products(job, item[0], item[2], item[3]))
            for item in parsed:
                name = item[0]
                if "Product_BOM" in name:
                    counts.update(self._import_bom(job, name, item[2], item[3]))
                elif "Process_Routing" in name:
                    counts.update(self._import_route(job, name, item[2], item[3]))
                elif "Equipment_Ledger" in name:
                    counts.update(self._import_equipment(job, name, item[2], item[3]))
                elif "Supplier_Profile" in name:
                    counts.update(self._import_suppliers(job, name, item[2], item[3]))
                elif "Capability_Baseline" in name:
                    self._scan_test_records(job, name, item[2], item[3])

            errors = self.db.scalar(
                select(func.count()).select_from(ImportIssue).where(
                    ImportIssue.import_job_id == job.id,
                    ImportIssue.severity == "error",
                )
            )
            job.status = ImportStatus.failed if errors else ImportStatus.validated
            job.summary = dict(counts)
            job.completed_at = datetime.now(timezone.utc)
            record_audit(
                self.db,
                actor=actor,
                action="import.completed",
                object_type="import_job",
                object_id=job.id,
                after_hash=hash_payload({"manifest": manifest, "summary": dict(counts)}),
                details={"status": job.status.value},
            )
            self.db.flush()
            IMPORTS.labels(job.status.value).inc()
            return job
        except Exception as exc:
            raise ImportProcessingError(
                job_id=job.id,
                actor=actor,
                manifest=manifest,
                cause=exc,
            ) from exc

    @staticmethod
    def _is_factor_file(name: str) -> bool:
        return any(token in name for token in ("原材料碳因子", "过程能源碳因子", "物流与废弃碳因子"))

    def _import_factors(
        self, job: ImportJob, file_name: str, headers: list[str], rows: list[dict[str, Any]]
    ) -> Counter:
        counts = Counter()
        material_col = _header(headers, "Material Code", required=False)
        name_col = _header(headers, "Name (CN/EN)", required=False) or _header(
            headers, "Energy Type", required=False
        ) or _header(headers, "Type (CN/EN)", required=False)
        unit_col = _header(headers, "Unit")
        value_col = _header(headers, "Factor Value")
        co2e_col = _header(headers, "CO2e Unit")
        source_col = _header(headers, "Source")
        standard_col = _header(headers, "Standard", required=False)
        category_col = _header(headers, "Category", required=False)
        quality_col = _header(headers, "Data Quality", required=False)
        region_col = _header(headers, "Region", required=False)
        year_col = _header(headers, "Year", required=False)

        for index, row in enumerate(rows, start=2):
            material_code = _text(row.get(material_col)) if material_col else ""
            name = _text(row.get(name_col)) if name_col else f"Factor row {index}"
            factor_code = _factor_code(material_code) if material_code else f"CF-{hash_payload(name)[:12]}"
            if material_code:
                material = self.db.scalar(select(Material).where(Material.code == material_code))
                if not material:
                    material = Material(
                        code=material_code,
                        name=name,
                        category=_text(row.get(category_col)) if category_col else None,
                    )
                    self.db.add(material)
                    self.db.flush()
                    counts["materials"] += 1

            factor = self.db.scalar(select(EmissionFactor).where(EmissionFactor.factor_code == factor_code))
            if not factor:
                factor = EmissionFactor(factor_code=factor_code, material_code=material_code or None, name=name)
                self.db.add(factor)
                self.db.flush()
            payload = {
                "value": _text(row.get(value_col)),
                "activity_unit": _text(row.get(unit_col)),
                "co2e_unit": _text(row.get(co2e_col)),
                "source": _text(row.get(source_col)),
                "standard": _text(row.get(standard_col)) if standard_col else None,
                "region": _text(row.get(region_col)) if region_col else None,
                "year": row.get(year_col) if year_col else None,
                "quality": _text(row.get(quality_col)) if quality_col else None,
            }
            content_hash = hash_payload(payload)
            existing = self.db.scalar(
                select(FactorVersion).where(
                    FactorVersion.factor_id == factor.id,
                    FactorVersion.content_hash == content_hash,
                )
            )
            if existing:
                continue
            version = _next_version(self.db, FactorVersion, FactorVersion.factor_id, factor.id)
            self.db.add(
                FactorVersion(
                    factor_id=factor.id,
                    version=version,
                    value=as_decimal(row.get(value_col)),
                    activity_unit=_text(row.get(unit_col)),
                    co2e_unit=_text(row.get(co2e_col)),
                    source=_text(row.get(source_col)),
                    standard=_text(row.get(standard_col)) if standard_col else None,
                    region=_text(row.get(region_col)) if region_col else None,
                    reference_year=int(row.get(year_col)) if year_col and row.get(year_col) else None,
                    data_quality=_text(row.get(quality_col)) if quality_col else None,
                    content_hash=content_hash,
                    approved=False,
                )
            )
            counts["factor_versions"] += 1
            if as_decimal(row.get(value_col), default=as_decimal(0)) < 0:
                _issue(
                    self.db,
                    job,
                    "warning",
                    file_name,
                    "NEGATIVE_FACTOR_REVIEW",
                    f"{factor_code} has a negative factor and requires LCA method review",
                    index,
                    value_col,
                )
        return counts

    def _import_products(
        self, job: ImportJob, file_name: str, headers: list[str], rows: list[dict[str, Any]]
    ) -> Counter:
        counts = Counter()
        sku_col = _header(headers, "Internal ID")
        brand_col = _header(headers, "Brand SKU")
        name_col = _header(headers, "Name (CN/EN)")
        market_col = _header(headers, "Market")
        for index, row in enumerate(rows, start=2):
            sku = _text(row.get(sku_col))
            if not sku:
                _issue(self.db, job, "error", file_name, "MISSING_SKU", "Product SKU is required", index, sku_col)
                continue
            product = self.db.scalar(select(Product).where(Product.sku == sku))
            if not product:
                product = Product(
                    sku=sku,
                    brand_sku=_text(row.get(brand_col)),
                    name=_text(row.get(name_col)),
                    target_market=_text(row.get(market_col)),
                )
                self.db.add(product)
                self.db.flush()
                counts["products"] += 1
            payload = json_safe({k: row.get(k) for k in headers})
            content_hash = hash_payload(payload)
            existing = self.db.scalar(
                select(ProductVersion).where(
                    ProductVersion.product_id == product.id,
                    ProductVersion.content_hash == content_hash,
                )
            )
            if not existing:
                self.db.add(
                    ProductVersion(
                        product_id=product.id,
                        version=_next_version(self.db, ProductVersion, ProductVersion.product_id, product.id),
                        source_import_id=job.id,
                        payload=payload,
                        content_hash=content_hash,
                    )
                )
                counts["product_versions"] += 1
        self.db.flush()
        return counts

    def _latest_product_version(self, sku: str) -> ProductVersion | None:
        return self.db.scalar(
            select(ProductVersion)
            .join(Product)
            .where(Product.sku == sku)
            .order_by(ProductVersion.version.desc())
        )

    def _import_bom(
        self, job: ImportJob, file_name: str, headers: list[str], rows: list[dict[str, Any]]
    ) -> Counter:
        counts = Counter()
        sku_col = _header(headers, "Internal ID")
        part_col = _header(headers, "Part Name")
        type_col = _header(headers, "Type")
        material_col = _header(headers, "Material Code")
        qty_col = _header(headers, "Qty")
        unit_col = _header(headers, "Unit")
        weight_col = _header(headers, "Weight")
        cf_col = _header(headers, "CF ID")
        line_counter: Counter[str] = Counter()
        for index, row in enumerate(rows, start=2):
            sku = _text(row.get(sku_col))
            product_version = self._latest_product_version(sku)
            if not product_version:
                _issue(self.db, job, "error", file_name, "UNKNOWN_PRODUCT", f"Unknown product: {sku}", index)
                continue
            line_counter[product_version.id] += 1
            material_code = _text(row.get(material_col))
            material = self.db.scalar(select(Material).where(Material.code == material_code))
            if not material:
                _issue(
                    self.db,
                    job,
                    "error",
                    file_name,
                    "UNKNOWN_MATERIAL",
                    f"Material not found in factor master: {material_code}",
                    index,
                    material_col,
                )
                continue
            factor_code = _text(row.get(cf_col)) or _factor_code(material_code)
            factor_version = self.db.scalar(
                select(FactorVersion)
                .join(EmissionFactor)
                .where(
                    EmissionFactor.factor_code == factor_code,
                    EmissionFactor.material_code == material_code,
                )
                .order_by(FactorVersion.version.desc())
            )
            if not factor_version:
                _issue(
                    self.db,
                    job,
                    "error",
                    file_name,
                    "FACTOR_MAPPING_MISSING",
                    f"No factor version for {material_code}/{factor_code}",
                    index,
                    cf_col,
                )
            stage = "packaging" if "包材" in _text(row.get(type_col)) or "Packaging" in _text(row.get(type_col)) else "raw_materials"
            existing = self.db.scalar(
                select(BomLine).where(
                    BomLine.product_version_id == product_version.id,
                    BomLine.line_no == line_counter[product_version.id],
                )
            )
            if existing:
                continue
            self.db.add(
                BomLine(
                    product_version_id=product_version.id,
                    line_no=line_counter[product_version.id],
                    material_id=material.id,
                    part_name=_text(row.get(part_col)),
                    material_type=_text(row.get(type_col)),
                    quantity=as_decimal(row.get(qty_col)),
                    unit=_text(row.get(unit_col)),
                    weight_kg_each=as_decimal(row.get(weight_col)),
                    factor_version_id=factor_version.id if factor_version else None,
                    stage=stage,
                    source_row=index,
                )
            )
            counts["bom_lines"] += 1
        return counts

    def _import_route(
        self, job: ImportJob, file_name: str, headers: list[str], rows: list[dict[str, Any]]
    ) -> Counter:
        counts = Counter()
        product = self.db.scalar(select(Product).where(Product.sku == "INT-WD-001"))
        if not product:
            _issue(self.db, job, "error", file_name, "PILOT_PRODUCT_MISSING", "INT-WD-001 not imported")
            return counts
        existing = self.db.scalar(
            select(ProcessRoute).where(
                ProcessRoute.product_id == product.id,
                ProcessRoute.version == "WD-ROUTE-V1",
            )
        )
        if existing:
            return counts
        route = ProcessRoute(
            product_id=product.id,
            route_code="WARDROBE-GATE",
            version="WD-ROUTE-V1",
            approved=False,
        )
        self.db.add(route)
        self.db.flush()
        process_col = _header(headers, "Process ID")
        name_col = _header(headers, "Name (CN/EN)")
        time_col = _header(headers, "Std Time")
        energy_col = _header(headers, "Energy Factor")
        for seq, row in enumerate(reversed(rows), start=1):
            self.db.add(
                RouteStep(
                    route_id=route.id,
                    sequence=seq,
                    process_code=_text(row.get(process_col)),
                    name=_text(row.get(name_col)),
                    standard_time_min=as_decimal(row.get(time_col)),
                    energy_kwh_per_unit=as_decimal(row.get(energy_col)),
                )
            )
            counts["route_steps"] += 1
        counts["routes"] += 1
        return counts

    def _import_equipment(
        self, job: ImportJob, file_name: str, headers: list[str], rows: list[dict[str, Any]]
    ) -> Counter:
        counts = Counter()
        code_col = _header(headers, "Equip ID")
        process_col = _header(headers, "Process ID")
        name_col = _header(headers, "Name (CN/EN)")
        area_col = _header(headers, "Area")
        power_col = _header(headers, "Power")
        energy_col = _header(headers, "Energy Type")
        for row in rows:
            code = _text(row.get(code_col))
            if self.db.scalar(select(Equipment).where(Equipment.equipment_code == code)):
                continue
            process_code = _text(row.get(process_col))
            allocation_pool = (
                process_code.split("-")[0]
                if process_code.startswith(("AUX-", "ENV-", "UTIL-", "GREEN-"))
                else None
            )
            self.db.add(
                Equipment(
                    equipment_code=code,
                    process_code=None if allocation_pool else process_code,
                    name=_text(row.get(name_col)),
                    area=_text(row.get(area_col)),
                    rated_power_kw=as_decimal(row.get(power_col)),
                    energy_type=_text(row.get(energy_col)),
                    allocation_pool=allocation_pool,
                )
            )
            counts["equipment"] += 1
        return counts

    def _import_suppliers(
        self, job: ImportJob, file_name: str, headers: list[str], rows: list[dict[str, Any]]
    ) -> Counter:
        counts = Counter()
        code_col = _header(headers, "Supplier ID")
        name_col = _header(headers, "Name (CN/EN)")
        category_col = _header(headers, "Category")
        cert_col = _header(headers, "Certs")
        for row in rows:
            code = _text(row.get(code_col))
            if not code or self.db.scalar(select(Supplier).where(Supplier.supplier_code == code)):
                continue
            self.db.add(
                Supplier(
                    supplier_code=code,
                    name=_text(row.get(name_col)),
                    category=_text(row.get(category_col)),
                    certifications=_text(row.get(cert_col)),
                    is_test=code.upper().startswith("TEST"),
                )
            )
            counts["suppliers"] += 1
        return counts

    def _scan_test_records(
        self, job: ImportJob, file_name: str, headers: list[str], rows: list[dict[str, Any]]
    ) -> None:
        data_id_col = _header(headers, "Data_ID")
        for index, row in enumerate(rows, start=2):
            if _text(row.get(data_id_col)).upper().startswith("TEST"):
                _issue(
                    self.db,
                    job,
                    "warning",
                    file_name,
                    "TEST_RECORD_ISOLATED",
                    f"Test record {_text(row.get(data_id_col))} was not imported",
                    index,
                    data_id_col,
                )
