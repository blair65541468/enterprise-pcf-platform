from io import BytesIO
from datetime import datetime

from openpyxl import Workbook

from tests.conftest import auth


def workbook_bytes(headers, rows):
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    output = BytesIO()
    wb.save(output)
    return output.getvalue()


def test_excel_import_creates_product_and_factor(client):
    product = workbook_bytes(
        [
            "工厂内部编号 Internal ID",
            "品牌方 SKU Brand SKU",
            "产品名称 Name (CN/EN)",
            "目标市场 Market",
        ],
        [["INT-WD-001", "BRD-WD", "Wardrobe", "EU"]],
    )
    factor = workbook_bytes(
        [
            "物料编号 Material Code",
            "物料名称 Name (CN/EN)",
            "计量单位 Unit",
            "碳排放因子数值 Factor Value",
            "碳排单位 CO2e Unit",
            "数据来源 Source",
            "适用标准 Standard",
            "物料分类 Category",
            "数据质量 Data Quality",
        ],
        [["RM-PK-001", "Carton", "kg", 1.1, "kgCO2e/kg", "source", "ISO 14067", "Packaging", "Secondary"]],
    )
    response = client.post(
        "/v1/imports/excel",
        files=[
            ("files", ("R_D_01_Product_Master.xlsx", product, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
            ("files", ("01_原材料碳因子库.xlsx", factor, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
        ],
        headers=auth("owner", "data_submitter"),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "validated"
    assert payload["summary"]["products"] == 1
    assert payload["summary"]["factor_versions"] == 1


def test_excel_import_serializes_datetime_payload(client):
    product = workbook_bytes(
        [
            "Internal ID",
            "Brand SKU",
            "Name (CN/EN)",
            "Market",
            "Effective Date",
        ],
        [["INT-WD-001", "BRD-WD", "Wardrobe", "EU", datetime(2026, 6, 20, 8, 30)]],
    )

    response = client.post(
        "/v1/imports/excel",
        files=[
            (
                "files",
                (
                    "R_D_01_Product_Master.xlsx",
                    product,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            )
        ],
        headers=auth("owner", "data_submitter"),
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "validated"
