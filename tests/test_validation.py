from decimal import Decimal

from sqlalchemy import select

from app.models import FactorVersion, MaterialProcessMapping, TransportActivity
from tests.conftest import auth
from tests.helpers import seed_valid_pilot


def test_snapshot_blocks_missing_density_mapping_and_transport(client, db):
    _, _, raw_factor, _, _, _ = seed_valid_pilot(db)
    raw_factor.activity_unit = "m³"
    raw_factor.density_kg_m3 = None
    raw_factor.approved = True
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

