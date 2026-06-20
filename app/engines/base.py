from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol

from app.modules.calculations.contracts import CalculationInput, ModelTemplateConfig


@dataclass
class EngineContribution:
    dimension: str
    code: str
    name: str
    amount_kg_co2e: Decimal
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EngineResult:
    engine_version: str
    total_kg_co2e: Decimal
    iso_categories: dict[str, Decimal]
    stages: dict[str, Decimal]
    contributions: list[EngineContribution]
    raw: dict[str, Any]


class CalculationEngine(Protocol):
    name: str

    def health(self) -> dict[str, Any]: ...

    def calculate(
        self,
        calculation_input: CalculationInput,
        template: ModelTemplateConfig,
    ) -> EngineResult: ...
