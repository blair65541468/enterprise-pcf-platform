package com.airpaq.pcf.calculations;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

public interface CalculationEngine {

    String name();

    Map<String, Object> health();

    EngineResult calculate(EngineInput input, ModelTemplateConfig template);

    record EngineInput(Map<String, Object> snapshot, String impactMethod) {}

    record ModelTemplateConfig(
            String productSystemUuid,
            String impactMethodUuid,
            String databaseVersion,
            Map<String, Object> parameterSchema,
            Map<String, Map<String, Object>> parameterContexts,
            Map<String, List<String>> stageProcessUuids) {}

    record Contribution(
            String dimension,
            String code,
            String name,
            BigDecimal amountKgCo2e,
            Map<String, Object> metadata) {}

    record EngineResult(
            String engineVersion,
            BigDecimal totalKgCo2e,
            Map<String, BigDecimal> isoCategories,
            Map<String, BigDecimal> stages,
            List<Contribution> contributions,
            Map<String, Object> raw) {}
}
