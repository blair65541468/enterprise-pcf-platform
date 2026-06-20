from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from app.config import settings
from app.engines.openlca import OpenLcaRestEngine
from app.modules.calculations.contracts import CalculationInput, ModelTemplateConfig
from app.modules.snapshots.contracts import SnapshotPayload

pytestmark = pytest.mark.openlca_integration


@dataclass(frozen=True)
class OpenLcaTestCase:
    product_system_uuid: str
    impact_method_uuid: str
    impact_method: str
    parameters: dict[str, Decimal]
    parameter_contexts: dict[str, dict[str, Any]]
    stage_process_uuids: dict[str, list[str]]
    expected_total_kg_co2e: Decimal
    absolute_tolerance_kg_co2e: Decimal
    relative_tolerance: Decimal

    @property
    def tolerance(self) -> Decimal:
        return max(
            self.absolute_tolerance_kg_co2e,
            abs(self.expected_total_kg_co2e) * self.relative_tolerance,
        )


def _required_text(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        pytest.fail(f"openLCA test case field '{field}' must be a non-empty string")
    return value.strip()


def _uuid(payload: dict[str, Any], field: str) -> str:
    value = _required_text(payload, field)
    try:
        parsed = UUID(value)
    except ValueError as exc:
        pytest.fail(f"openLCA test case field '{field}' must be a valid UUID: {exc}")
    if parsed.int == 0:
        pytest.fail(
            f"openLCA test case field '{field}' still contains the example placeholder UUID"
        )
    return str(parsed)


def _decimal(
    payload: dict[str, Any],
    field: str,
    *,
    default: str | None = None,
    positive: bool = False,
) -> Decimal:
    value = payload.get(field, default)
    if isinstance(value, bool) or value is None:
        pytest.fail(f"openLCA test case field '{field}' must be numeric")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        pytest.fail(f"openLCA test case field '{field}' must be numeric: {exc}")
    if not parsed.is_finite():
        pytest.fail(f"openLCA test case field '{field}' must be finite")
    if positive and parsed <= 0:
        pytest.fail(f"openLCA test case field '{field}' must be greater than zero")
    return parsed


def _object(payload: dict[str, Any], field: str) -> dict[str, Any]:
    value = payload.get(field, {})
    if not isinstance(value, dict):
        pytest.fail(f"openLCA test case field '{field}' must be a JSON object")
    return value


def _load_test_case(path: Path) -> OpenLcaTestCase:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        pytest.fail(f"OPENLCA_TEST_CASE_FILE does not exist: {path}")
    except json.JSONDecodeError as exc:
        pytest.fail(f"OPENLCA_TEST_CASE_FILE is not valid JSON: {exc}")
    if not isinstance(payload, dict):
        pytest.fail("OPENLCA_TEST_CASE_FILE root must be a JSON object")

    raw_parameters = _object(payload, "parameters")
    parameters = {
        name: _decimal({"value": value}, "value")
        for name, value in raw_parameters.items()
        if isinstance(name, str) and name.strip()
    }
    if len(parameters) != len(raw_parameters):
        pytest.fail("openLCA parameter names must be non-empty strings")

    parameter_contexts = _object(payload, "parameter_contexts")
    if not all(
        isinstance(name, str) and name.strip() and isinstance(context, dict)
        for name, context in parameter_contexts.items()
    ):
        pytest.fail("parameter_contexts must map non-empty parameter names to JSON objects")
    unknown_contexts = set(parameter_contexts) - set(parameters)
    if unknown_contexts:
        pytest.fail(
            "parameter_contexts contains names absent from parameters: "
            + ", ".join(sorted(unknown_contexts))
        )

    raw_stage_process_uuids = _object(payload, "stage_process_uuids")
    stage_process_uuids: dict[str, list[str]] = {}
    for stage, process_ids in raw_stage_process_uuids.items():
        if not isinstance(stage, str) or not stage.strip() or not isinstance(process_ids, list):
            pytest.fail("stage_process_uuids must map stage names to UUID arrays")
        validated_ids: list[str] = []
        for process_id in process_ids:
            try:
                validated_ids.append(str(UUID(str(process_id))))
            except ValueError as exc:
                pytest.fail(f"invalid process UUID for stage '{stage}': {exc}")
        stage_process_uuids[stage] = validated_ids

    return OpenLcaTestCase(
        product_system_uuid=_uuid(payload, "product_system_uuid"),
        impact_method_uuid=_uuid(payload, "impact_method_uuid"),
        impact_method=_required_text(payload, "impact_method"),
        parameters=parameters,
        parameter_contexts=parameter_contexts,
        stage_process_uuids=stage_process_uuids,
        expected_total_kg_co2e=_decimal(payload, "expected_total_kg_co2e"),
        absolute_tolerance_kg_co2e=_decimal(
            payload,
            "absolute_tolerance_kg_co2e",
            default="0.01",
            positive=True,
        ),
        relative_tolerance=_decimal(
            payload,
            "relative_tolerance",
            default="0.001",
            positive=True,
        ),
    )


@pytest.fixture
def openlca_test_case() -> OpenLcaTestCase:
    openlca_url = os.environ.get("OPENLCA_URL", "").strip()
    if not openlca_url:
        pytest.fail("OPENLCA_URL must be set when --run-openlca is enabled")

    case_file = os.environ.get("OPENLCA_TEST_CASE_FILE", "").strip()
    if not case_file:
        pytest.fail("OPENLCA_TEST_CASE_FILE must be set when --run-openlca is enabled")

    return _load_test_case(Path(case_file).expanduser().resolve())


@pytest.fixture
def openlca_engine(
    monkeypatch: pytest.MonkeyPatch,
    openlca_test_case: OpenLcaTestCase,
) -> OpenLcaRestEngine:
    timeout_text = os.environ.get(
        "OPENLCA_TIMEOUT_SECONDS",
        str(settings.openlca_timeout_seconds),
    )
    try:
        timeout = int(timeout_text)
    except ValueError:
        pytest.fail("OPENLCA_TIMEOUT_SECONDS must be an integer")
    if timeout <= 0:
        pytest.fail("OPENLCA_TIMEOUT_SECONDS must be greater than zero")

    monkeypatch.setattr(settings, "openlca_url", os.environ["OPENLCA_URL"].rstrip("/"))
    monkeypatch.setattr(
        settings,
        "openlca_api_token",
        os.environ.get("OPENLCA_API_TOKEN") or None,
    )
    monkeypatch.setattr(settings, "openlca_timeout_seconds", timeout)
    return OpenLcaRestEngine()


def test_openlca_health(
    openlca_engine: OpenLcaRestEngine,
    openlca_test_case: OpenLcaTestCase,
):
    del openlca_test_case
    health = openlca_engine.health()

    assert health["status"] == "ok"
    assert health["engine"] == "openlca-rest"
    assert isinstance(health["version"], str)
    assert health["version"].strip()


def test_openlca_baseline_calculation(
    openlca_engine: OpenLcaRestEngine,
    openlca_test_case: OpenLcaTestCase,
):
    case = openlca_test_case
    result = openlca_engine.calculate(
        CalculationInput(
            snapshot=SnapshotPayload(
                sku="openlca-integration-test",
                product_name="openLCA integration test",
                functional_unit="configured test case",
                boundary="configured",
                factor_set_version="configured",
                product_version=1,
                route_version="configured",
                bom=[],
                energy=[],
                transport=[],
                openlca_parameters={
                    name: str(value) for name, value in case.parameters.items()
                },
                stage_estimates={},
            ),
            impact_method=case.impact_method,
        ),
        ModelTemplateConfig(
            product_system_uuid=case.product_system_uuid,
            impact_method_uuid=case.impact_method_uuid,
            database_version="openlca-integration-test",
            parameter_contexts=case.parameter_contexts,
            stage_process_uuids=case.stage_process_uuids,
        ),
    )

    assert result.engine_version.strip()
    assert result.total_kg_co2e.is_finite()
    assert math.isfinite(float(result.total_kg_co2e))
    assert all(value.is_finite() for value in result.iso_categories.values())
    assert all(value.is_finite() for value in result.stages.values())
    assert all(item.amount_kg_co2e.is_finite() for item in result.contributions)
    assert result.raw["product_system_uuid"] == case.product_system_uuid
    assert result.raw["impact_method_uuid"] == case.impact_method_uuid
    assert {
        name: Decimal(value) for name, value in result.raw["parameters"].items()
    } == case.parameters
    assert result.raw["stage_process_uuids"] == {
        stage: sorted(process_ids)
        for stage, process_ids in case.stage_process_uuids.items()
    }

    difference = abs(result.total_kg_co2e - case.expected_total_kg_co2e)
    assert difference <= case.tolerance, (
        f"openLCA baseline mismatch: actual={result.total_kg_co2e}, "
        f"expected={case.expected_total_kg_co2e}, "
        f"difference={difference}, tolerance={case.tolerance}"
    )
