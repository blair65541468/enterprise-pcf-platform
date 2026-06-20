from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.core.auth import Principal, get_principal, require_role
from app.core.clock import SystemClock
from app.core.config import Settings
from app.core.dependencies import calculation_engine, clock, object_storage
from app.models import (
    AuditEvent,
    BomLine,
    CalculationRun,
    CalculationStatus,
    EmissionFactor,
    FactorVersion,
    Material,
    MaterialProcessMapping,
    OutboxEvent,
    ProcessRoute,
    TransportActivity,
)
from app.modules.catalog.units import UnitConversionError, convert_activity_amount
from app.modules.imports.excel import ExcelImportAdapter
from app.services.outbox_service import OutboxService
from app.storage import LocalObjectStorage, ObjectStorage
from app.tasks import calculate_run
from app.utils import sha256_bytes
from tests.conftest import auth
from tests.helpers import seed_valid_pilot
from tests.test_import import workbook_bytes


def _snapshot(client):
    return client.post(
        "/v1/products/INT-WD-001/snapshots",
        json={},
        headers=auth("owner", "data_submitter"),
    ).json()


def _calculation_request(snapshot, key: str) -> dict:
    return {
        "sku": "INT-WD-001",
        "snapshot_version": snapshot["version"],
        "model_template_version": "WARDROBE-GATE-V1",
        "factor_set_version": "2026.06",
        "route_version": "WD-ROUTE-V1",
        "impact_method": "IPCC-2021-ISO14067-GWP100",
        "boundary": "cradle_to_gate_with_packaging",
        "idempotency_key": key,
    }


def test_units_are_explicit_and_never_guess():
    assert convert_activity_amount(
        quantity=Decimal("2"),
        weight_kg_each=Decimal("3"),
        activity_unit="kg",
        density_kg_m3=None,
    ) == Decimal("6")
    assert convert_activity_amount(
        quantity=Decimal("2"),
        weight_kg_each=Decimal("3"),
        activity_unit="m3",
        density_kg_m3=Decimal("600"),
    ) == Decimal("0.01")
    with pytest.raises(UnitConversionError):
        convert_activity_amount(
            quantity=Decimal("1"),
            weight_kg_each=Decimal("1"),
            activity_unit="m3",
            density_kg_m3=None,
        )
    with pytest.raises(UnitConversionError):
        convert_activity_amount(
            quantity=Decimal("1"),
            weight_kg_each=Decimal("1"),
            activity_unit="piece",
            density_kg_m3=None,
        )


def test_excel_adapter_produces_source_neutral_batch():
    data = workbook_bytes(["Code", "Code"], [["A", "B"]])
    batch = ExcelImportAdapter().parse([("source.xlsx", data)])
    assert batch.source == "excel"
    assert batch.files[0].headers == ("Code", "Code__2")
    assert batch.files[0].rows == ({"Code": "A", "Code__2": "B"},)
    assert batch.files[0].sha256 == sha256_bytes(data)
    assert ExcelImportAdapter().parse(
        [("empty.xlsx", workbook_bytes([], []))]
    ).files[0].rows == ()


def test_request_id_health_and_metrics(client):
    response = client.get("/health/live", headers={"X-Request-ID": "test-request-id"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-id"
    assert client.get("/health").json() == {"status": "ok"}
    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json()["checks"]["task_broker"]["mode"] == "eager"
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "pcf_http_requests_total" in metrics.text


def test_core_dependencies_auth_and_local_storage(tmp_path):
    principal = get_principal(
        credentials=None,
        x_user_id="reviewer",
        x_roles="lca_reviewer",
    )
    assert principal.subject == "reviewer"
    assert require_role("lca_reviewer")(principal) is principal
    with pytest.raises(HTTPException):
        require_role("admin")(Principal("user", frozenset()))  # type: ignore[arg-type]
    assert calculation_engine().name == "mock"
    assert object_storage().health()["status"] == "ok"
    assert isinstance(clock(), SystemClock)
    assert SystemClock().now().tzinfo is not None

    storage = LocalObjectStorage(tmp_path)
    assert storage.put("folder/value.txt", b"value", "text/plain") == "folder/value.txt"
    assert storage.get("folder/value.txt") == b"value"
    assert storage.health() == {"status": "ok", "backend": "local"}
    with pytest.raises(ValueError):
        storage.put("../outside.txt", b"bad")
    with pytest.raises(NotImplementedError):
        ObjectStorage().put("key", b"value")
    with pytest.raises(NotImplementedError):
        ObjectStorage().get("key")
    with pytest.raises(NotImplementedError):
        ObjectStorage().health()


def test_production_configuration_rejects_unsafe_defaults():
    with pytest.raises(ValueError, match="SQLite is not allowed"):
        Settings(app_env="production")
    safe = Settings(
        app_env="production",
        database_url="postgresql+psycopg://pcf:pcf@postgres/pcf",
        celery_task_always_eager=False,
        local_auth_enabled=False,
        oidc_enabled=True,
        oidc_jwks_url="https://identity.example/jwks",
        object_storage_backend="s3",
        s3_secret_key="not-a-default",
    )
    assert safe.is_production


def test_reused_idempotency_key_with_different_request_returns_409(client, db):
    seed_valid_pilot(db)
    snapshot = _snapshot(client)
    request = _calculation_request(snapshot, "strict-idempotency")
    first = client.post(
        "/v1/calculations",
        json=request,
        headers=auth("owner", "data_submitter"),
    )
    assert first.status_code == 200
    request["impact_method"] = "DIFFERENT-METHOD"
    second = client.post(
        "/v1/calculations",
        json=request,
        headers=auth("owner", "data_submitter"),
    )
    assert second.status_code == 409
    assert second.json()["detail"] == (
        "Idempotency key was already used for a different calculation request"
    )


def test_duplicate_task_delivery_is_ignored(client, db):
    seed_valid_pilot(db)
    snapshot = _snapshot(client)
    response = client.post(
        "/v1/calculations",
        json=_calculation_request(snapshot, "duplicate-delivery"),
        headers=auth("owner", "data_submitter"),
    )
    run_id = response.json()["id"]
    calculate_run.delay(run_id)
    db.expire_all()
    run = db.get(CalculationRun, run_id)
    events = list(
        db.scalars(
            select(AuditEvent).where(
                AuditEvent.object_id == run_id,
                AuditEvent.action == "calculation.completed",
            )
        )
    )
    assert run.attempt_count == 1
    assert len(events) == 1
    outbox = db.scalar(select(OutboxEvent).where(OutboxEvent.aggregate_id == run_id))
    assert outbox.published_at is not None


def test_outbox_reuses_event_and_recovers_stale_run(client, db):
    seed_valid_pilot(db)
    snapshot = _snapshot(client)
    response = client.post(
        "/v1/calculations",
        json=_calculation_request(snapshot, "outbox-recovery"),
        headers=auth("owner", "data_submitter"),
    )
    run = db.get(CalculationRun, response.json()["id"])
    service = OutboxService(db)
    event = service.enqueue_calculation(run.id, "request-2")
    assert event.published_at is None
    assert event.payload["request_id"] == "request-2"
    service.mark_failed(event, RuntimeError("broker unavailable"))
    assert event.attempt_count >= 1
    assert event.last_error == "broker unavailable"
    run.status = CalculationStatus.calculating
    run.heartbeat_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
    db.flush()
    assert service.recover_stale_calculations() == 1
    assert run.status == CalculationStatus.queued
    assert event.published_at is None


def test_approved_factor_is_immutable(db):
    _, _, factor, _, _, _ = seed_valid_pilot(db)
    factor.source = "attempted mutation"
    with pytest.raises(ValueError, match="immutable"):
        db.commit()
    db.rollback()


def test_admin_endpoints_remain_compatible(client, db):
    _, _, raw_factor, _, _, truck_factor = seed_valid_pilot(db)
    factor_entity = db.get(EmissionFactor, raw_factor.factor_id)
    draft = FactorVersion(
        factor_id=factor_entity.id,
        version=2,
        value=raw_factor.value,
        activity_unit="m3",
        co2e_unit="kgCO2e/m3",
        source="review source",
        content_hash="draft",
        approved=False,
    )
    db.add(draft)
    db.commit()

    approved = client.post(
        f"/v1/admin/factors/{factor_entity.factor_code}/approve",
        json={"density_kg_m3": "650", "licence_ref": "internal-review"},
        headers=auth("reviewer", "lca_reviewer"),
    )
    assert approved.status_code == 200
    assert approved.json()["version"] == 2

    mapping = client.post(
        "/v1/admin/mappings/materials",
        json={
            "material_code": "RM-WD-001",
            "process_uuid": "process-v2",
            "reference_flow_uuid": "flow-v2",
            "openlca_unit": "kg",
            "conversion_rule": {"type": "identity"},
            "database_version": "test-db-v2",
        },
        headers=auth("reviewer", "lca_reviewer"),
    )
    assert mapping.status_code == 200

    transport = client.post(
        "/v1/admin/products/INT-WD-001/transport-activities",
        json={
            "mode": "Truck",
            "distance_km": "20",
            "mass_kg": "10",
            "load_factor": "0.8",
            "factor_code": truck_factor.factor.factor_code,
            "source": "ERP",
        },
        headers=auth("reviewer", "lca_reviewer"),
    )
    assert transport.status_code == 200

    route = client.post(
        "/v1/admin/products/INT-WD-001/routes/WD-ROUTE-V1/approve",
        headers=auth("reviewer", "lca_reviewer"),
    )
    assert route.status_code == 200

    template = client.post(
        "/v1/admin/model-templates",
        json={
            "code": "WARDROBE-GATE-V2",
            "name": "Wardrobe V2",
            "product_family": "wardrobe",
            "version": "WARDROBE-GATE-V2",
            "product_system_uuid": "product-system-v2",
            "impact_method_uuid": "impact-method-v2",
            "database_version": "test-db-v2",
            "parameter_schema": {},
        },
        headers=auth("reviewer", "lca_reviewer"),
    )
    assert template.status_code == 200
    assert client.post(
        "/v1/admin/model-templates",
        json={
            "code": "WARDROBE-GATE-V2",
            "name": "Wardrobe V2",
            "product_family": "wardrobe",
            "version": "WARDROBE-GATE-V2",
            "product_system_uuid": "product-system-v2",
            "impact_method_uuid": "impact-method-v2",
            "database_version": "test-db-v2",
        },
        headers=auth("reviewer", "lca_reviewer"),
    ).status_code == 409

    assert db.scalar(select(Material).where(Material.code == "RM-WD-001"))
    assert db.scalar(select(MaterialProcessMapping).where(MaterialProcessMapping.database_version == "test-db-v2"))
    assert db.scalar(select(TransportActivity).where(TransportActivity.mode == "Truck"))
    assert db.scalar(select(ProcessRoute).where(ProcessRoute.version == "WD-ROUTE-V1"))
    assert db.scalar(select(BomLine))
