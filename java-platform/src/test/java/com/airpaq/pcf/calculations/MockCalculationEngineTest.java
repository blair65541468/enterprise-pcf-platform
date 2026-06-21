package com.airpaq.pcf.calculations;

import static org.assertj.core.api.Assertions.assertThat;

import com.airpaq.pcf.calculations.domain.CalculationEngine;
import com.airpaq.pcf.calculations.infrastructure.engine.MockCalculationEngine;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class MockCalculationEngineTest {

    @Test
    void calculatesDeterministicStageAndIsoTotals() {
        var snapshot =
                Map.<String, Object>of(
                        "bom",
                        List.of(
                                Map.of(
                                        "activity_amount", "2",
                                        "factor_value", "3",
                                        "stage", "raw_materials",
                                        "material_code", "RM-1",
                                        "part_name", "Board",
                                        "factor_activity_unit", "kg",
                                        "factor_code", "CF-1")),
                        "energy",
                        List.of(
                                Map.of(
                                        "amount", "1",
                                        "factor_value", "0.5",
                                        "process_code", "PROC-1",
                                        "name", "Manufacturing",
                                        "factor_code", "CF-GRID")),
                        "transport",
                        List.of(
                                Map.of(
                                        "mass_kg", "2.5",
                                        "distance_km", "100",
                                        "factor_value", "0.1",
                                        "mode", "Truck",
                                        "factor_code", "CF-TRUCK")));
        var template =
                new CalculationEngine.ModelTemplateConfig(
                        "ps", "method", "db", Map.of(), Map.of(), Map.of());

        var result =
                new MockCalculationEngine()
                        .calculate(new CalculationEngine.EngineInput(snapshot, "GWP100"), template);

        assertThat(result.totalKgCo2e()).isEqualByComparingTo(new BigDecimal("6.525"));
        assertThat(result.stages().get("raw_materials")).isEqualByComparingTo("6");
        assertThat(result.stages().get("manufacturing")).isEqualByComparingTo("0.5");
        assertThat(result.stages().get("inbound_transport")).isEqualByComparingTo("0.025");
        assertThat(result.isoCategories().get("fossil")).isEqualByComparingTo(result.totalKgCo2e());
        assertThat(result.contributions()).hasSize(3);
    }
}
