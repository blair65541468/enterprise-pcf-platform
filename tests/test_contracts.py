from pathlib import Path

from app.main import app
from app.schemas import CalculationCreate
from app.utils import canonical_json, sha256_bytes


def test_openapi_contract_snapshot():
    expected = (
        Path(__file__).with_name("openapi.snapshot.sha256").read_text(encoding="utf-8").strip()
    )
    actual = sha256_bytes(canonical_json(app.openapi()))
    assert actual == expected, (
        "The public OpenAPI contract changed. Preserve /v1 compatibility or deliberately "
        "review and update tests/openapi.snapshot.sha256."
    )


def test_legacy_schema_import_remains_available():
    model = CalculationCreate(snapshot_version=1, idempotency_key="legacy-compatible")
    assert model.snapshot_version == 1
