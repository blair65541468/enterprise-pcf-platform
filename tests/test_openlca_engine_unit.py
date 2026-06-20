from decimal import Decimal
from types import SimpleNamespace

import httpx
import olca_schema as o
import pytest

from app.core.exceptions import ExternalServiceError
from app.engines.openlca import OpenLcaRestEngine
from app.modules.calculations.contracts import CalculationInput, ModelTemplateConfig
from app.modules.snapshots.contracts import SnapshotPayload


def ref(uid: str, name: str, ref_type: o.RefType) -> o.Ref:
    return o.Ref(id=uid, name=name, ref_type=ref_type)


class FakeResult:
    def __init__(self, *, error: str | None = None):
        self.error = error
        self.disposed = False

    def wait_until_ready(self):
        return SimpleNamespace(error=self.error)

    def get_total_impacts(self):
        return [
            SimpleNamespace(
                impact_category=ref("climate", "Climate change", o.RefType.ImpactCategory),
                amount=5,
            ),
            SimpleNamespace(
                impact_category=ref("fossil", "Fossil", o.RefType.ImpactCategory),
                amount=5,
            ),
        ]

    def get_impact_contributions_of(self, _category):
        return [
            SimpleNamespace(
                amount=3,
                tech_flow=SimpleNamespace(
                    provider=ref("process-raw", "Raw material", o.RefType.Process),
                    flow=None,
                ),
            ),
            SimpleNamespace(
                amount=2,
                tech_flow=SimpleNamespace(
                    provider=ref("process-manufacturing", "Manufacturing", o.RefType.Process),
                    flow=None,
                ),
            ),
        ]

    def dispose(self):
        self.disposed = True


class FakeClient:
    def __init__(self, *, product=True, method=True, result=None):
        self.product = product
        self.method = method
        self.result = result or FakeResult()
        self.setup = None

    def get_descriptor(self, model_type, uid):
        if model_type is o.ProductSystem:
            return ref(uid, "Product system", o.RefType.ProductSystem) if self.product else None
        return ref(uid, "Impact method", o.RefType.ImpactMethod) if self.method else None

    def calculate(self, setup):
        self.setup = setup
        return self.result


def input_and_template():
    calculation_input = CalculationInput(
        snapshot=SnapshotPayload(
            sku="SKU",
            product_name="Product",
            functional_unit="1 product",
            boundary="cradle-to-gate",
            factor_set_version="1",
            product_version=1,
            route_version="1",
            bom=[],
            energy=[],
            transport=[],
            openlca_parameters={"mass": "2"},
            stage_estimates={},
        ),
        impact_method="GWP100",
    )
    template = ModelTemplateConfig(
        product_system_uuid="product-system",
        impact_method_uuid="impact-method",
        database_version="db-v1",
        parameter_contexts={
            "mass": {
                "@type": "Process",
                "@id": "parameter-process",
                "name": "Parameter process",
            }
        },
        stage_process_uuids={
            "raw_materials": ["process-raw"],
            "manufacturing": ["process-manufacturing"],
        },
    )
    return calculation_input, template


def test_openlca_engine_calculates_and_disposes(monkeypatch):
    engine = OpenLcaRestEngine()
    client = FakeClient()
    monkeypatch.setattr(engine, "_client", lambda: client)
    monkeypatch.setattr(engine, "_version", lambda: "2.0.28")
    calculation_input, template = input_and_template()

    result = engine.calculate(calculation_input, template)

    assert result.engine_version == "2.0.28"
    assert result.total_kg_co2e == Decimal("5")
    assert result.iso_categories["fossil"] == Decimal("5")
    assert result.stages["raw_materials"] == Decimal("3")
    assert result.stages["manufacturing"] == Decimal("2")
    assert client.setup.parameters[0].context.id == "parameter-process"
    assert client.result.disposed


@pytest.mark.parametrize(
    ("product", "method", "code"),
    [
        (False, True, "OPENLCA_PRODUCT_SYSTEM_NOT_FOUND"),
        (True, False, "OPENLCA_IMPACT_METHOD_NOT_FOUND"),
    ],
)
def test_openlca_engine_reports_missing_models(monkeypatch, product, method, code):
    engine = OpenLcaRestEngine()
    monkeypatch.setattr(
        engine,
        "_client",
        lambda: FakeClient(product=product, method=method),
    )
    calculation_input, template = input_and_template()
    with pytest.raises(ExternalServiceError) as error:
        engine.calculate(calculation_input, template)
    assert error.value.code == code


def test_openlca_engine_reports_calculation_error_and_disposes(monkeypatch):
    engine = OpenLcaRestEngine()
    client = FakeClient(result=FakeResult(error="solver failed"))
    monkeypatch.setattr(engine, "_client", lambda: client)
    calculation_input, template = input_and_template()
    with pytest.raises(ExternalServiceError, match="solver failed"):
        engine.calculate(calculation_input, template)
    assert client.result.disposed


def test_openlca_engine_normalizes_transport_errors(monkeypatch):
    engine = OpenLcaRestEngine()
    calculation_input, template = input_and_template()

    def timeout(*_args):
        raise httpx.ReadTimeout("slow")

    monkeypatch.setattr(engine, "_calculate", timeout)
    with pytest.raises(ExternalServiceError) as timeout_error:
        engine.calculate(calculation_input, template)
    assert timeout_error.value.code == "OPENLCA_TIMEOUT"

    def unreachable(*_args):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(engine, "_calculate", unreachable)
    with pytest.raises(ExternalServiceError) as connection_error:
        engine.calculate(calculation_input, template)
    assert connection_error.value.code == "OPENLCA_UNREACHABLE"


def test_openlca_health_normalizes_version_transport_errors(monkeypatch):
    engine = OpenLcaRestEngine()

    def timeout(*_args, **_kwargs):
        raise httpx.ReadTimeout("slow")

    monkeypatch.setattr(httpx, "get", timeout)
    with pytest.raises(ExternalServiceError) as error:
        engine.health()
    assert error.value.code == "OPENLCA_TIMEOUT"


def test_openlca_result_helpers_cover_named_categories():
    engine = OpenLcaRestEngine()
    impacts = {
        "Aircraft": Decimal("1"),
        "Biogenic emissions": Decimal("2"),
        "Biogenic removals": Decimal("-1"),
        "Fossil": Decimal("3"),
        "Land use change": Decimal("0.5"),
    }
    categories = engine._iso_categories(impacts, Decimal("5.5"))
    assert categories == {
        "aircraft": Decimal("1"),
        "biogenic_emissions": Decimal("2"),
        "biogenic_removals": Decimal("-1"),
        "fossil": Decimal("3"),
        "land_use_change": Decimal("0.5"),
    }
    assert engine._pick_total({"Total": Decimal("1")}) == Decimal("1")
    assert engine._pick_total({"GWP 100": Decimal("2")}) == Decimal("2")
    with pytest.raises(RuntimeError, match="No Total"):
        engine._pick_total({"Acidification": Decimal("3")})
