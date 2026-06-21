package com.airpaq.pcf.calculations.infrastructure.engine;

import com.airpaq.pcf.calculations.domain.CalculationEngine;
import com.airpaq.pcf.shared.config.PcfProperties;
import com.airpaq.pcf.shared.web.DomainException;
import java.math.BigDecimal;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
@ConditionalOnProperty(name = "pcf.openlca.engine", havingValue = "rest")
public class OpenLcaRestEngine implements CalculationEngine {

    private final RestClient client;
    private final Duration timeout;

    public OpenLcaRestEngine(RestClient.Builder builder, PcfProperties properties) {
        var config = properties.openlca();
        this.timeout = config.timeout();
        var factory = new JdkClientHttpRequestFactory();
        factory.setReadTimeout(timeout);
        this.client =
                builder.baseUrl(config.url().toString())
                        .requestFactory(factory)
                        .defaultHeader(
                                "X-API-TOKEN", config.apiToken() == null ? "" : config.apiToken())
                        .build();
    }

    @Override
    public String name() {
        return "openlca-rest";
    }

    @Override
    public Map<String, Object> health() {
        var version = get("/api/version");
        return Map.of(
                "status", "ok",
                "engine", name(),
                "version", String.valueOf(version.get("version")));
    }

    @Override
    @SuppressWarnings("unchecked")
    public EngineResult calculate(EngineInput input, ModelTemplateConfig template) {
        var product = descriptor("product-systems", template.productSystemUuid());
        var method = descriptor("impact-methods", template.impactMethodUuid());
        var parameters =
                (Map<String, Object>) input.snapshot().getOrDefault("openlca_parameters", Map.of());
        var redefinitions = new ArrayList<Map<String, Object>>();
        parameters.forEach(
                (name, value) -> {
                    var redefine = new LinkedHashMap<String, Object>();
                    redefine.put("name", name);
                    redefine.put("value", new BigDecimal(String.valueOf(value)));
                    var context = template.parameterContexts().get(name);
                    if (context != null) {
                        redefine.put("context", context);
                    }
                    redefinitions.add(redefine);
                });
        var setup =
                Map.of(
                        "target", product,
                        "impactMethod", method,
                        "parameters", redefinitions);
        var state = post("/result/calculate", setup);
        var resultId = string(state, "@id", "id");
        if (resultId == null) {
            throw new DomainException(502, "openLCA returned no result handle");
        }
        try {
            waitUntilReady(resultId);
            var impacts = getList("/result/" + resultId + "/total-impacts");
            var impactMap = new LinkedHashMap<String, BigDecimal>();
            Map<String, Object> totalCategory = null;
            for (var item : impacts) {
                var category = map(item.get("impactCategory"), item.get("impact_category"));
                var name = String.valueOf(category.get("name"));
                impactMap.put(name, decimal(item.get("amount")));
                if (isTotalName(name)) {
                    totalCategory = category;
                }
            }
            var total = pickTotal(impactMap);
            var contributions = new ArrayList<Contribution>();
            if (totalCategory != null) {
                var categoryId = string(totalCategory, "@id", "id");
                for (var item :
                        getList("/result/" + resultId + "/impact-contributions-of/" + categoryId)) {
                    var techFlow = map(item.get("techFlow"), item.get("tech_flow"));
                    var provider = map(techFlow.get("provider"), techFlow.get("flow"));
                    contributions.add(
                            new Contribution(
                                    "openlca_process",
                                    value(provider, "@id", "id"),
                                    value(provider, "name"),
                                    decimal(item.get("amount")),
                                    Map.of()));
                }
            }
            var stages = stageTotals(contributions, template.stageProcessUuids(), input.snapshot());
            return new EngineResult(
                    String.valueOf(health().get("version")),
                    total,
                    isoCategories(impactMap, total),
                    stages,
                    contributions,
                    Map.of(
                            "total_impacts", impactMap,
                            "product_system_uuid", template.productSystemUuid(),
                            "impact_method_uuid", template.impactMethodUuid(),
                            "parameters", parameters,
                            "stage_process_uuids", template.stageProcessUuids()));
        } finally {
            try {
                post("/result/" + resultId + "/dispose", Map.of());
            } catch (RuntimeException ignored) {
                // The calculation result must never hide the original failure.
            }
        }
    }

    private Map<String, Object> descriptor(String type, String id) {
        try {
            return get("/data/" + type + "/" + id + "/info");
        } catch (RuntimeException exception) {
            throw new DomainException(502, "openLCA model not found: " + id);
        }
    }

    private void waitUntilReady(String id) {
        var deadline = System.nanoTime() + timeout.toNanos();
        while (System.nanoTime() < deadline) {
            var state = get("/result/" + id + "/state");
            if (state.get("error") != null) {
                throw new DomainException(502, "openLCA calculation failed: " + state.get("error"));
            }
            if (Boolean.TRUE.equals(state.get("isReady"))
                    || Boolean.TRUE.equals(state.get("is_ready"))) {
                return;
            }
            try {
                Thread.sleep(250);
            } catch (InterruptedException exception) {
                Thread.currentThread().interrupt();
                throw new DomainException(502, "openLCA polling interrupted");
            }
        }
        throw new DomainException(504, "openLCA calculation timed out");
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> get(String path) {
        try {
            return client.get().uri(path).retrieve().body(Map.class);
        } catch (RestClientException exception) {
            throw new DomainException(
                    502, "openLCA service is unavailable: " + exception.getMessage());
        }
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> getList(String path) {
        try {
            return client.get().uri(path).retrieve().body(List.class);
        } catch (RestClientException exception) {
            throw new DomainException(
                    502, "openLCA result request failed: " + exception.getMessage());
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> post(String path, Object body) {
        try {
            return client.post().uri(path).body(body).retrieve().body(Map.class);
        } catch (RestClientException exception) {
            throw new DomainException(502, "openLCA request failed: " + exception.getMessage());
        }
    }

    private static BigDecimal pickTotal(Map<String, BigDecimal> impacts) {
        return impacts.entrySet().stream()
                .filter(entry -> isTotalName(entry.getKey()))
                .map(Map.Entry::getValue)
                .findFirst()
                .orElseThrow(
                        () ->
                                new DomainException(
                                        502, "No Total/Climate change/GWP100 result found"));
    }

    private static boolean isTotalName(String name) {
        var lowered = name.toLowerCase();
        return lowered.equals("total")
                || lowered.contains("climate change")
                || lowered.contains("gwp 100");
    }

    private static Map<String, BigDecimal> isoCategories(
            Map<String, BigDecimal> impacts, BigDecimal total) {
        var result = new LinkedHashMap<String, BigDecimal>();
        result.put("aircraft", BigDecimal.ZERO);
        result.put("biogenic_emissions", BigDecimal.ZERO);
        result.put("biogenic_removals", BigDecimal.ZERO);
        result.put("fossil", BigDecimal.ZERO);
        result.put("land_use_change", BigDecimal.ZERO);
        impacts.forEach(
                (name, amount) -> {
                    var lowered = name.toLowerCase();
                    if (lowered.contains("aircraft")) result.put("aircraft", amount);
                    else if (lowered.contains("biogenic emissions"))
                        result.put("biogenic_emissions", amount);
                    else if (lowered.contains("biogenic removals"))
                        result.put("biogenic_removals", amount);
                    else if (lowered.contains("fossil")) result.put("fossil", amount);
                    else if (lowered.contains("land use")) result.put("land_use_change", amount);
                });
        if (result.values().stream().allMatch(BigDecimal.ZERO::equals)) {
            result.put("fossil", total);
        }
        return result;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, BigDecimal> stageTotals(
            List<Contribution> contributions,
            Map<String, List<String>> groups,
            Map<String, Object> snapshot) {
        var result = new LinkedHashMap<String, BigDecimal>();
        result.put("raw_materials", BigDecimal.ZERO);
        result.put("inbound_transport", BigDecimal.ZERO);
        result.put("manufacturing", BigDecimal.ZERO);
        result.put("packaging", BigDecimal.ZERO);
        if (groups != null && !groups.isEmpty()) {
            contributions.forEach(
                    contribution ->
                            groups.forEach(
                                    (stage, ids) -> {
                                        if (ids.contains(contribution.code())) {
                                            result.merge(
                                                    stage,
                                                    contribution.amountKgCo2e(),
                                                    BigDecimal::add);
                                        }
                                    }));
            return result;
        }
        var estimates = (Map<String, Object>) snapshot.getOrDefault("stage_estimates", Map.of());
        estimates.forEach((stage, amount) -> result.put(stage, decimal(amount)));
        return result;
    }

    private static BigDecimal decimal(Object value) {
        return new BigDecimal(String.valueOf(value));
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> map(Object first, Object second) {
        var value = first == null ? second : first;
        return value instanceof Map<?, ?> raw ? (Map<String, Object>) raw : Map.of();
    }

    private static String string(Map<String, Object> value, String... keys) {
        for (var key : keys) {
            if (value.get(key) != null) return String.valueOf(value.get(key));
        }
        return null;
    }

    private static String value(Map<String, Object> value, String... keys) {
        var result = string(value, keys);
        return result == null ? "" : result;
    }
}
