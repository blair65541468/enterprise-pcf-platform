package com.airpaq.pcf.calculations.infrastructure.engine;

import com.airpaq.pcf.calculations.domain.CalculationEngine;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(name = "pcf.openlca.engine", havingValue = "mock", matchIfMissing = true)
public class MockCalculationEngine implements CalculationEngine {

    @Override
    public String name() {
        return "mock";
    }

    @Override
    public Map<String, Object> health() {
        return Map.of(
                "status", "ok",
                "engine", name(),
                "version", "deterministic-factor-1");
    }

    @Override
    @SuppressWarnings("unchecked")
    public EngineResult calculate(EngineInput input, ModelTemplateConfig template) {
        var stages = new LinkedHashMap<String, BigDecimal>();
        stages.put("raw_materials", BigDecimal.ZERO);
        stages.put("inbound_transport", BigDecimal.ZERO);
        stages.put("manufacturing", BigDecimal.ZERO);
        stages.put("packaging", BigDecimal.ZERO);
        var contributions = new ArrayList<Contribution>();

        for (var item : list(input.snapshot().get("bom"))) {
            var amount =
                    decimal(item.get("activity_amount"))
                            .multiply(decimal(item.get("factor_value")));
            var stage = String.valueOf(item.get("stage"));
            stages.merge(stage, amount, BigDecimal::add);
            contributions.add(
                    new Contribution(
                            "material",
                            String.valueOf(item.get("material_code")),
                            String.valueOf(item.get("part_name")),
                            amount,
                            Map.of(
                                    "activity_amount",
                                    item.get("activity_amount"),
                                    "activity_unit",
                                    item.get("factor_activity_unit"),
                                    "factor_code",
                                    item.get("factor_code"))));
        }
        for (var item : list(input.snapshot().get("energy"))) {
            var amount = decimal(item.get("amount")).multiply(decimal(item.get("factor_value")));
            stages.merge("manufacturing", amount, BigDecimal::add);
            contributions.add(
                    new Contribution(
                            "process",
                            String.valueOf(item.get("process_code")),
                            String.valueOf(item.get("name")),
                            amount,
                            Map.of(
                                    "energy_kwh",
                                    item.get("amount"),
                                    "factor_code",
                                    item.get("factor_code"))));
        }
        for (var item : list(input.snapshot().get("transport"))) {
            var tkm =
                    decimal(item.get("mass_kg"))
                            .divide(new BigDecimal("1000"))
                            .multiply(decimal(item.get("distance_km")));
            var amount = tkm.multiply(decimal(item.get("factor_value")));
            stages.merge("inbound_transport", amount, BigDecimal::add);
            contributions.add(
                    new Contribution(
                            "transport",
                            String.valueOf(item.get("mode")),
                            item.get("mode") + " - " + valueOr(item.get("material_code"), "all"),
                            amount,
                            Map.of(
                                    "tkm",
                                    tkm.toPlainString(),
                                    "factor_code",
                                    item.get("factor_code"))));
        }
        contributions.sort(
                Comparator.comparing(
                                (Contribution contribution) -> contribution.amountKgCo2e().abs())
                        .reversed());
        var total = stages.values().stream().reduce(BigDecimal.ZERO, BigDecimal::add);
        return new EngineResult(
                "deterministic-factor-1",
                total,
                Map.of(
                        "aircraft", BigDecimal.ZERO,
                        "biogenic_emissions", BigDecimal.ZERO,
                        "biogenic_removals", BigDecimal.ZERO,
                        "fossil", total,
                        "land_use_change", BigDecimal.ZERO),
                stages,
                contributions,
                Map.of(
                        "engine",
                        "mock",
                        "warning",
                        "This deterministic engine is for integration tests only, not an ISO 14067 result.",
                        "impact_method",
                        input.impactMethod(),
                        "template",
                        template));
    }

    private static List<Map<String, Object>> list(Object value) {
        return value instanceof List<?> raw
                ? raw.stream().map(item -> (Map<String, Object>) item).toList()
                : List.of();
    }

    private static BigDecimal decimal(Object value) {
        return new BigDecimal(String.valueOf(value));
    }

    private static Object valueOr(Object value, Object fallback) {
        return value == null ? fallback : value;
    }
}
