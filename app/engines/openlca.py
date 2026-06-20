from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx
import olca_ipc.rest as rest
import olca_schema as o
import requests

from app.config import settings
from app.core.exceptions import ExternalServiceError
from app.core.metrics import OPENLCA_ERRORS
from app.engines.base import EngineContribution, EngineResult
from app.modules.calculations.contracts import CalculationInput, ModelTemplateConfig


class OpenLcaRestEngine:
    name = "openlca-rest"

    def _client(self) -> rest.RestClient:
        headers = {"X-API-TOKEN": settings.openlca_api_token} if settings.openlca_api_token else None
        return rest.RestClient(
            settings.openlca_url,
            headers=headers,
            timeout=settings.openlca_timeout_seconds,
        )

    def _version(self) -> str:
        headers = {"X-API-TOKEN": settings.openlca_api_token} if settings.openlca_api_token else None
        try:
            response = httpx.get(
                f"{settings.openlca_url.rstrip('/')}/api/version",
                headers=headers,
                timeout=20,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            OPENLCA_ERRORS.labels("timeout").inc()
            raise ExternalServiceError(
                f"openLCA version request timed out: {exc}",
                code="OPENLCA_TIMEOUT",
            ) from exc
        except httpx.TransportError as exc:
            OPENLCA_ERRORS.labels("unreachable").inc()
            raise ExternalServiceError(
                f"openLCA service is unreachable: {exc}",
                code="OPENLCA_UNREACHABLE",
            ) from exc
        data = response.json()
        return str(data.get("version") if isinstance(data, dict) else data)

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "engine": self.name, "version": self._version()}

    def calculate(
        self,
        calculation_input: CalculationInput,
        template: ModelTemplateConfig,
    ) -> EngineResult:
        try:
            return self._calculate(calculation_input, template)
        except ExternalServiceError:
            raise
        except (httpx.TimeoutException, requests.Timeout, TimeoutError) as exc:
            OPENLCA_ERRORS.labels("timeout").inc()
            raise ExternalServiceError(
                f"openLCA request timed out: {exc}",
                code="OPENLCA_TIMEOUT",
            ) from exc
        except (httpx.TransportError, requests.ConnectionError) as exc:
            OPENLCA_ERRORS.labels("unreachable").inc()
            raise ExternalServiceError(
                f"openLCA service is unreachable: {exc}",
                code="OPENLCA_UNREACHABLE",
            ) from exc

    def _calculate(
        self,
        calculation_input: CalculationInput,
        template: ModelTemplateConfig,
    ) -> EngineResult:
        client = self._client()
        snapshot = calculation_input.snapshot.model_dump(mode="json")
        product_system_uuid = template.product_system_uuid
        impact_method_uuid = template.impact_method_uuid
        product_system = client.get_descriptor(o.ProductSystem, product_system_uuid)
        method = client.get_descriptor(o.ImpactMethod, impact_method_uuid)
        if product_system is None:
            OPENLCA_ERRORS.labels("model_missing").inc()
            raise ExternalServiceError(
                f"openLCA ProductSystem not found: {product_system_uuid}",
                code="OPENLCA_PRODUCT_SYSTEM_NOT_FOUND",
            )
        if method is None:
            OPENLCA_ERRORS.labels("model_missing").inc()
            raise ExternalServiceError(
                f"openLCA ImpactMethod not found: {impact_method_uuid}",
                code="OPENLCA_IMPACT_METHOD_NOT_FOUND",
            )

        redefs = []
        parameters = snapshot.get("openlca_parameters", {})
        contexts = template.parameter_contexts
        for name, value in parameters.items():
            context = contexts.get(name)
            redefs.append(
                o.ParameterRedef(
                    name=name,
                    value=float(value),
                    context=o.Ref.from_dict(context) if context else None,
                )
            )
        setup = o.CalculationSetup(
            target=product_system,
            impact_method=method,
            parameters=redefs,
        )
        result = client.calculate(setup)
        if result is None:
            raise RuntimeError("openLCA returned no result handle")
        try:
            state = result.wait_until_ready()
            if getattr(state, "error", None):
                OPENLCA_ERRORS.labels("calculation").inc()
                raise ExternalServiceError(
                    f"openLCA calculation failed: {state.error}",
                    code="OPENLCA_CALCULATION_FAILED",
                )
            impacts = result.get_total_impacts()
            impact_map = {
                item.impact_category.name: Decimal(str(item.amount))
                for item in impacts
                if item.impact_category and item.impact_category.name
            }
            total = self._pick_total(impact_map)
            iso = self._iso_categories(impact_map, total)
            contributions: list[EngineContribution] = []
            total_ref = next(
                (
                    item.impact_category
                    for item in impacts
                    if item.impact_category
                    and self._is_total_name(item.impact_category.name or "")
                ),
                None,
            )
            if total_ref:
                for value in result.get_impact_contributions_of(total_ref):
                    flow = value.tech_flow
                    code = ""
                    name = "Unnamed process"
                    if flow:
                        if flow.provider:
                            code = flow.provider.id or ""
                            name = flow.provider.name or name
                        elif flow.flow:
                            code = flow.flow.id or ""
                            name = flow.flow.name or name
                    contributions.append(
                        EngineContribution(
                            dimension="openlca_process",
                            code=code,
                            name=name,
                            amount_kg_co2e=Decimal(str(value.amount)),
                        )
                    )
            stage_groups = {
                stage: set(process_ids)
                for stage, process_ids in template.stage_process_uuids.items()
            }
            if stage_groups:
                stages = {
                    "raw_materials": Decimal("0"),
                    "inbound_transport": Decimal("0"),
                    "manufacturing": Decimal("0"),
                    "packaging": Decimal("0"),
                }
                for item in contributions:
                    for stage, process_ids in stage_groups.items():
                        if item.code in process_ids:
                            stages.setdefault(stage, Decimal("0"))
                            stages[stage] += item.amount_kg_co2e
            else:
                # Kept only as a controlled fallback. CalculationService rejects the
                # result if these estimates do not reconcile with the openLCA total.
                stages = {
                    key: Decimal(str(value))
                    for key, value in snapshot.get("stage_estimates", {}).items()
                }
            return EngineResult(
                engine_version=self._version(),
                total_kg_co2e=total,
                iso_categories=iso,
                stages=stages,
                contributions=contributions,
                raw={
                    "total_impacts": {
                        key: str(value) for key, value in impact_map.items()
                    },
                    "product_system_uuid": product_system_uuid,
                    "impact_method_uuid": impact_method_uuid,
                    "parameters": {k: str(v) for k, v in parameters.items()},
                    "stage_process_uuids": {
                        key: sorted(value) for key, value in stage_groups.items()
                    },
                },
            )
        finally:
            result.dispose()

    @staticmethod
    def _is_total_name(name: str) -> bool:
        lowered = name.lower()
        return lowered == "total" or "climate change" in lowered or "gwp 100" in lowered

    def _pick_total(self, impacts: dict[str, Decimal]) -> Decimal:
        for name, value in impacts.items():
            if name.lower() == "total":
                return value
        for name, value in impacts.items():
            if "climate change" in name.lower() or "gwp 100" in name.lower():
                return value
        raise RuntimeError("No Total/Climate change/GWP100 result found in openLCA response")

    @staticmethod
    def _iso_categories(impacts: dict[str, Decimal], total: Decimal) -> dict[str, Decimal]:
        result = {
            "aircraft": Decimal("0"),
            "biogenic_emissions": Decimal("0"),
            "biogenic_removals": Decimal("0"),
            "fossil": Decimal("0"),
            "land_use_change": Decimal("0"),
        }
        for name, value in impacts.items():
            lowered = name.lower()
            if "aircraft" in lowered:
                result["aircraft"] = value
            elif "biogenic emissions" in lowered:
                result["biogenic_emissions"] = value
            elif "biogenic removals" in lowered:
                result["biogenic_removals"] = value
            elif "fossil" in lowered:
                result["fossil"] = value
            elif "land use" in lowered:
                result["land_use_change"] = value
        if all(value == 0 for value in result.values()):
            result["fossil"] = total
        return result
