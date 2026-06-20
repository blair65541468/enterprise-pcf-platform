from decimal import Decimal
from typing import Any

from app.engines.base import EngineContribution, EngineResult
from app.modules.calculations.contracts import CalculationInput, ModelTemplateConfig


class MockCalculationEngine:
    name = "mock"

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "engine": self.name, "version": "deterministic-factor-1"}

    def calculate(
        self,
        calculation_input: CalculationInput,
        template: ModelTemplateConfig,
    ) -> EngineResult:
        snapshot = calculation_input.snapshot.model_dump(mode="json")
        contributions: list[EngineContribution] = []
        stages = {
            "raw_materials": Decimal("0"),
            "inbound_transport": Decimal("0"),
            "manufacturing": Decimal("0"),
            "packaging": Decimal("0"),
        }
        for item in snapshot["bom"]:
            amount = Decimal(item["activity_amount"]) * Decimal(item["factor_value"])
            stage = item["stage"]
            stages[stage] += amount
            contributions.append(
                EngineContribution(
                    dimension="material",
                    code=item["material_code"],
                    name=item["part_name"],
                    amount_kg_co2e=amount,
                    metadata={
                        "activity_amount": item["activity_amount"],
                        "activity_unit": item["factor_activity_unit"],
                        "factor_code": item["factor_code"],
                    },
                )
            )
        for item in snapshot.get("energy", []):
            amount = Decimal(item["amount"]) * Decimal(item["factor_value"])
            stages["manufacturing"] += amount
            contributions.append(
                EngineContribution(
                    dimension="process",
                    code=item["process_code"],
                    name=item["name"],
                    amount_kg_co2e=amount,
                    metadata={"energy_kwh": item["amount"], "factor_code": item["factor_code"]},
                )
            )
        for item in snapshot.get("transport", []):
            tkm = Decimal(item["mass_kg"]) / Decimal("1000") * Decimal(item["distance_km"])
            amount = tkm * Decimal(item["factor_value"])
            stages["inbound_transport"] += amount
            contributions.append(
                EngineContribution(
                    dimension="transport",
                    code=item["mode"],
                    name=f"{item['mode']} - {item.get('material_code') or 'all'}",
                    amount_kg_co2e=amount,
                    metadata={"tkm": str(tkm), "factor_code": item["factor_code"]},
                )
            )
        total = sum(stages.values(), Decimal("0"))
        contributions.sort(key=lambda x: abs(x.amount_kg_co2e), reverse=True)
        return EngineResult(
            engine_version="deterministic-factor-1",
            total_kg_co2e=total,
            iso_categories={
                "aircraft": Decimal("0"),
                "biogenic_emissions": Decimal("0"),
                "biogenic_removals": Decimal("0"),
                "fossil": total,
                "land_use_change": Decimal("0"),
            },
            stages=stages,
            contributions=contributions,
            raw={
                "engine": "mock",
                "warning": "This deterministic engine is for integration tests only, not an ISO 14067 result.",
                "impact_method": calculation_input.impact_method,
                "template": template.model_dump(mode="json"),
            },
        )
