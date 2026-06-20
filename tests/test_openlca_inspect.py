from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace

import olca_schema as o
import pytest

from scripts.openlca_inspect import (
    build_case_template,
    calculate_impacts,
    descriptor_rows,
    main,
    parameter_rows,
    write_case_template,
)


def ref(uid: str, name: str, ref_type: o.RefType) -> o.Ref:
    return o.Ref(id=uid, name=name, ref_type=ref_type)


class FakeClient:
    def __init__(self):
        self.descriptors = {
            o.ProductSystem: [
                ref("ps-2", "Wardrobe Z", o.RefType.ProductSystem),
                ref("ps-1", "Wardrobe A", o.RefType.ProductSystem),
                ref("ps-3", "Chair", o.RefType.ProductSystem),
            ],
            o.ImpactMethod: [
                ref("im-1", "IPCC GWP 100", o.RefType.ImpactMethod),
            ],
            o.Process: [],
        }
        context = ref("process-1", "Parameter process", o.RefType.Process)
        self.parameters = [
            o.ParameterRedef(name="mass", value=2.5, context=context),
            o.ParameterRedef(name="distance", value=100),
        ]
        self.result = None

    def get_descriptors(self, model_type):
        return self.descriptors[model_type]

    def get_descriptor(self, model_type, uid=None, name=None):
        del name
        return next(
            (item for item in self.descriptors[model_type] if item.id == uid),
            None,
        )

    def get_parameters(self, model_type, uid):
        assert model_type is o.ProductSystem
        assert uid == "ps-1"
        return self.parameters

    def calculate(self, setup):
        self.result = FakeResult(setup)
        return self.result


@dataclass
class FakeImpact:
    impact_category: o.Ref
    amount: float


class FakeResult:
    def __init__(self, setup):
        self.setup = setup
        self.disposed = False

    def wait_until_ready(self):
        return SimpleNamespace(error=None)

    def get_total_impacts(self):
        return [
            FakeImpact(ref("ic-1", "Climate change", o.RefType.ImpactCategory), 1.25)
        ]

    def dispose(self):
        self.disposed = True


def test_descriptor_rows_filter_and_sort():
    rows = descriptor_rows(FakeClient(), o.ProductSystem, "wardrobe")

    assert [row["id"] for row in rows] == ["ps-1", "ps-2"]
    assert rows[0]["ref_type"] == "ProductSystem"


def test_parameter_rows_include_serialized_context():
    rows = parameter_rows(FakeClient(), "ps-1")

    assert rows[0]["name"] == "distance"
    assert rows[1]["context"] == {
        "@type": "Process",
        "@id": "process-1",
        "name": "Parameter process",
    }


def test_list_command_supports_json_output(capsys, tmp_path):
    exit_code = main(
        [
            "--env-file",
            str(tmp_path / "missing.env"),
            "list-product-systems",
            "--filter",
            "wardrobe",
            "--json",
        ],
        client_factory=lambda config: FakeClient(),
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert [item["id"] for item in payload] == ["ps-1", "ps-2"]


def test_case_template_has_unapproved_baseline_and_refuses_overwrite(tmp_path):
    payload = build_case_template(FakeClient(), "ps-1", "im-1")
    output = tmp_path / "openlca-case.local.json"

    assert payload["expected_total_kg_co2e"] is None
    assert payload["parameters"] == {"distance": 100, "mass": 2.5}
    assert payload["parameter_contexts"]["mass"]["@id"] == "process-1"

    write_case_template(output, payload)
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        write_case_template(output, payload)


def test_calculation_disposes_result():
    client = FakeClient()

    rows = calculate_impacts(
        client,
        "ps-1",
        "im-1",
        parameters={"mass": 2.5},
        parameter_contexts={
            "mass": {
                "@type": "Process",
                "@id": "process-1",
                "name": "Parameter process",
            }
        },
    )

    assert rows == [{"id": "ic-1", "name": "Climate change", "amount": "1.25"}]
    assert client.result.disposed is True
    assert client.result.setup.parameters[0].context.id == "process-1"
