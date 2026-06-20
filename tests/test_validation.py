
from sqlalchemy import select

from app.models import BomLine, FactorVersion, MaterialProcessMapping, TransportActivity
from app.utils import hash_payload
from tests.conftest import auth
from tests.helpers import seed_valid_pilot


def test_snapshot_blocks_missing_density_mapping_and_transport(client, db):
    _, _, raw_factor, _, _, _ = seed_valid_pilot(db)
    volume_factor = FactorVersion(
        factor_id=raw_factor.factor_id,
        version=2,
        value=raw_factor.value,
        activity_unit="m³",
        co2e_unit="kgCO2e/m³",
        source=raw_factor.source,
        standard=raw_factor.standard,
        region=raw_factor.region,
        reference_year=raw_factor.reference_year,
        data_quality=raw_factor.data_quality,
        density_kg_m3=None,
        content_hash=hash_payload({"factor": raw_factor.factor_id, "version": 2}),
        approved=True,
    )
    db.add(volume_factor)
    db.flush()
    bom_line = db.scalar(
        select(BomLine).where(BomLine.factor_version_id == raw_factor.id)
    )
    bom_line.factor_version_id = volume_factor.id
    mapping = db.scalar(select(MaterialProcessMapping).where(MaterialProcessMapping.process_uuid.like("%RM-WD-001")))
    db.delete(mapping)
    db.query(TransportActivity).delete()
    db.commit()

    response = client.post(
        "/v1/products/INT-WD-001/snapshots",
        json={},
        headers=auth("owner", "data_submitter"),
    )
    assert response.status_code == 422
    codes = {item["code"] for item in response.json()["detail"]["errors"]}
    assert {"DENSITY_MISSING", "INBOUND_TRANSPORT_MISSING"} <= codes
