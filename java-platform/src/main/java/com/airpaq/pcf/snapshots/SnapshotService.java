package com.airpaq.pcf.snapshots;

import com.airpaq.pcf.audit.AuditService;
import com.airpaq.pcf.infrastructure.api.ApiContracts.SnapshotCreate;
import com.airpaq.pcf.infrastructure.api.ApiContracts.SnapshotOut;
import com.airpaq.pcf.infrastructure.json.CanonicalJson;
import com.airpaq.pcf.infrastructure.web.DomainException;
import java.math.BigDecimal;
import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class SnapshotService {

    private static final BigDecimal ZERO = BigDecimal.ZERO;

    private final JdbcTemplate jdbc;
    private final CanonicalJson canonicalJson;
    private final AuditService audit;
    private final Clock clock = Clock.systemUTC();

    public SnapshotService(JdbcTemplate jdbc, CanonicalJson canonicalJson, AuditService audit) {
        this.jdbc = jdbc;
        this.canonicalJson = canonicalJson;
        this.audit = audit;
    }

    @Transactional
    public SnapshotOut create(String sku, SnapshotCreate request, String actor) {
        var product =
                one(
                        """
                        select id, sku, name from product where sku = ?
                        """,
                        sku);
        if (product == null) throw DomainException.notFound("Unknown product: " + sku);
        var productVersion =
                one(
                        """
                        select id, version from product_version
                        where product_id = ? order by version desc limit 1
                        """,
                        product.get("id"));
        if (productVersion == null) {
            throw DomainException.unprocessable("Product has no version");
        }
        var route =
                one(
                        """
                        select id, approved from process_route
                        where product_id = ? and version = ?
                        """,
                        product.get("id"),
                        request.routeVersion());
        var errors = new ArrayList<Map<String, Object>>();
        if (route == null) {
            errors.add(
                    Map.of(
                            "code",
                            "ROUTE_MISSING",
                            "message",
                            "Route " + request.routeVersion() + " not found"));
        } else if (!Boolean.TRUE.equals(route.get("approved"))) {
            errors.add(
                    Map.of(
                            "code",
                            "ROUTE_NOT_APPROVED",
                            "message",
                            "Route " + request.routeVersion() + " is not approved"));
        }

        var stages = stageMap();
        var parameters = new LinkedHashMap<String, String>();
        var bomPayload = new ArrayList<Map<String, Object>>();
        var bom =
                jdbc.queryForList(
                        """
                        select b.line_no, b.material_id, b.part_name, b.quantity, b.unit,
                               b.weight_kg_each, b.stage, m.code material_code,
                               f.factor_code, fv.version factor_version, fv.value factor_value,
                               fv.activity_unit, fv.source factor_source, fv.approved factor_approved,
                               fv.density_kg_m3,
                               mp.process_uuid, mp.reference_flow_uuid, mp.openlca_unit,
                               mp.database_version
                        from bom_line b
                        join material m on m.id = b.material_id
                        left join factor_version fv on fv.id = b.factor_version_id
                        left join emission_factor f on f.id = fv.factor_id
                        left join lateral (
                          select * from material_process_mapping x
                          where x.material_id = b.material_id and x.status = 'approved'
                          order by x.created_at desc limit 1
                        ) mp on true
                        where b.product_version_id = ?
                        order by b.line_no
                        """,
                        productVersion.get("id"));
        if (bom.isEmpty()) {
            errors.add(Map.of("code", "BOM_MISSING", "message", "Product has no BOM lines"));
        }
        for (var line : bom) {
            var lineNo = ((Number) line.get("line_no")).intValue();
            if (line.get("factor_value") == null) {
                errors.add(
                        Map.of(
                                "code",
                                "FACTOR_MISSING",
                                "line",
                                lineNo,
                                "material",
                                line.get("material_code")));
                continue;
            }
            if (!Boolean.TRUE.equals(line.get("factor_approved"))) {
                errors.add(
                        Map.of(
                                "code",
                                "FACTOR_NOT_APPROVED",
                                "line",
                                lineNo,
                                "factor",
                                line.get("factor_code")));
            }
            if (line.get("weight_kg_each") == null) {
                errors.add(Map.of("code", "BOM_WEIGHT_MISSING", "line", lineNo));
                continue;
            }
            var quantity = decimal(line.get("quantity"));
            var weight = decimal(line.get("weight_kg_each"));
            var mass = quantity.multiply(weight);
            var unit = String.valueOf(line.get("activity_unit"));
            BigDecimal activity;
            if (unit.equalsIgnoreCase("kg") || unit.equalsIgnoreCase("kilogram")) {
                activity = mass;
            } else if (unit.equalsIgnoreCase("m3") || unit.equalsIgnoreCase("m³")) {
                if (line.get("density_kg_m3") == null) {
                    errors.add(
                            Map.of(
                                    "code",
                                    "DENSITY_MISSING",
                                    "line",
                                    lineNo,
                                    "material",
                                    line.get("material_code")));
                    continue;
                }
                activity =
                        mass.divide(
                                        decimal(line.get("density_kg_m3")),
                                        12,
                                        java.math.RoundingMode.HALF_UP)
                                .stripTrailingZeros();
            } else {
                errors.add(
                        Map.of(
                                "code",
                                "UNIT_CONVERSION_MISSING",
                                "line",
                                lineNo,
                                "from",
                                line.get("unit"),
                                "to",
                                unit));
                continue;
            }
            if (line.get("process_uuid") == null) {
                errors.add(
                        Map.of(
                                "code",
                                "OPENLCA_MAPPING_MISSING",
                                "line",
                                lineNo,
                                "material",
                                line.get("material_code")));
            }
            var stage = String.valueOf(line.get("stage"));
            stages.merge(
                    stage, activity.multiply(decimal(line.get("factor_value"))), BigDecimal::add);
            var parameterName =
                    "mat_"
                            + String.valueOf(line.get("material_code"))
                                    .toLowerCase()
                                    .replace("-", "_");
            parameters.put(parameterName, plain(activity));
            var payload = new LinkedHashMap<String, Object>();
            payload.put("line_no", lineNo);
            payload.put("material_code", line.get("material_code"));
            payload.put("part_name", line.get("part_name"));
            payload.put("stage", stage);
            payload.put("quantity", plain(quantity));
            payload.put("unit", line.get("unit"));
            payload.put("weight_kg_each", plain(weight));
            payload.put("mass_kg", plain(mass));
            payload.put("factor_code", line.get("factor_code"));
            payload.put("factor_version", line.get("factor_version"));
            payload.put("factor_value", plain(decimal(line.get("factor_value"))));
            payload.put("factor_activity_unit", unit);
            payload.put("factor_source", line.get("factor_source"));
            payload.put("activity_amount", plain(activity));
            payload.put(
                    "mapping",
                    line.get("process_uuid") == null
                            ? null
                            : Map.of(
                                    "process_uuid", line.get("process_uuid"),
                                    "reference_flow_uuid", line.get("reference_flow_uuid"),
                                    "openlca_unit", line.get("openlca_unit"),
                                    "database_version", line.get("database_version")));
            bomPayload.add(payload);
        }

        var energyPayload =
                energyPayload(
                        String.valueOf(productVersion.get("id")),
                        route == null ? null : String.valueOf(route.get("id")),
                        errors,
                        stages,
                        parameters);
        var transportPayload =
                transportPayload(
                        String.valueOf(productVersion.get("id")), errors, stages, parameters);
        if (!errors.isEmpty()) {
            throw DomainException.unprocessable(
                    Map.of("code", "SNAPSHOT_INVALID", "errors", errors));
        }
        var payload = new LinkedHashMap<String, Object>();
        payload.put("schema_version", 1);
        payload.put("sku", sku);
        payload.put("product_name", product.get("name"));
        payload.put(
                "functional_unit",
                "1 completed and packaged " + product.get("name") + " at factory gate");
        payload.put("boundary", request.boundary());
        payload.put("factor_set_version", request.factorSetVersion());
        payload.put("product_version", productVersion.get("version"));
        payload.put("route_version", request.routeVersion());
        payload.put("bom", bomPayload);
        payload.put("energy", energyPayload);
        payload.put("transport", transportPayload);
        payload.put("openlca_parameters", parameters);
        payload.put(
                "stage_estimates",
                stages.entrySet().stream()
                        .collect(
                                java.util.stream.Collectors.toMap(
                                        Map.Entry::getKey,
                                        entry -> plain(entry.getValue()),
                                        (left, right) -> right,
                                        LinkedHashMap::new)));
        var hash = canonicalJson.sha256(payload);
        var version =
                jdbc.queryForObject(
                        "select coalesce(max(version), 0) + 1 from calculation_snapshot where product_id = ?",
                        Integer.class,
                        product.get("id"));
        var id = UUID.randomUUID().toString();
        var now = java.sql.Timestamp.from(Instant.now(clock));
        jdbc.update(
                """
                insert into calculation_snapshot
                  (id, product_id, version, product_version_id, route_id,
                   factor_set_version, boundary, payload, manifest_hash,
                   validation_errors, created_by, created_at)
                values (?, ?, ?, ?, ?, ?, ?, ?::json, ?, '[]'::json, ?, ?)
                """,
                id,
                product.get("id"),
                version,
                productVersion.get("id"),
                route.get("id"),
                request.factorSetVersion(),
                request.boundary(),
                canonicalJson.string(payload),
                hash,
                actor,
                now);
        audit.record(
                actor,
                "snapshot.created",
                "calculation_snapshot",
                id,
                null,
                hash,
                Map.of("sku", sku, "version", version));
        return new SnapshotOut(
                id,
                version,
                request.factorSetVersion(),
                request.boundary(),
                hash,
                List.of(),
                now.toInstant());
    }

    private List<Map<String, Object>> energyPayload(
            String productVersionId,
            String routeId,
            List<Map<String, Object>> errors,
            Map<String, BigDecimal> stages,
            Map<String, String> parameters) {
        var activities =
                jdbc.queryForList(
                        """
                        select ea.*, rs.process_code, rs.name, fv.value factor_value,
                               f.factor_code
                        from energy_activity ea
                        left join route_step rs on rs.id = ea.route_step_id
                        left join factor_version fv on fv.id = ea.factor_version_id
                        left join emission_factor f on f.id = fv.factor_id
                        where ea.product_version_id = ?
                        """,
                        productVersionId);
        if (activities.isEmpty() && routeId != null) {
            var factor =
                    one(
                            """
                            select fv.id factor_version_id, fv.value factor_value,
                                   f.factor_code
                            from factor_version fv join emission_factor f on f.id = fv.factor_id
                            where fv.approved = true
                              and (f.name ilike '%Grid Electricity%' or f.name ilike '%市电%')
                            order by fv.version desc limit 1
                            """);
            if (factor == null) {
                errors.add(
                        Map.of(
                                "code", "GRID_FACTOR_MISSING",
                                "message", "Approved grid factor is required"));
                return List.of();
            }
            activities =
                    jdbc.queryForList(
                            """
                            select process_code, name, coalesce(energy_kwh_per_unit, 0) amount,
                                   'approved route standard' source
                            from route_step where route_id = ? order by sequence
                            """,
                            routeId);
            for (var item : activities) {
                item.putAll(factor);
                item.put("approved", true);
            }
        }
        var payload = new ArrayList<Map<String, Object>>();
        for (var item : activities) {
            if (item.containsKey("approved") && !Boolean.TRUE.equals(item.get("approved"))) {
                errors.add(Map.of("code", "ENERGY_ACTIVITY_NOT_APPROVED", "id", item.get("id")));
            }
            if (item.get("factor_value") == null) {
                errors.add(
                        Map.of(
                                "code",
                                "ENERGY_FACTOR_NOT_APPROVED",
                                "process",
                                item.get("process_code")));
                continue;
            }
            var amount = decimal(item.get("amount"));
            stages.merge(
                    "manufacturing",
                    amount.multiply(decimal(item.get("factor_value"))),
                    BigDecimal::add);
            var code = String.valueOf(item.getOrDefault("process_code", "ENERGY"));
            parameters.put("energy_" + code.toLowerCase().replace("-", "_"), plain(amount));
            payload.add(
                    Map.of(
                            "process_code", code,
                            "name",
                                    item.getOrDefault(
                                            "name", item.getOrDefault("energy_type", "Energy")),
                            "amount", plain(amount),
                            "unit", "kWh",
                            "factor_code", item.get("factor_code"),
                            "factor_value", plain(decimal(item.get("factor_value"))),
                            "source", item.get("source")));
        }
        return payload;
    }

    private List<Map<String, Object>> transportPayload(
            String productVersionId,
            List<Map<String, Object>> errors,
            Map<String, BigDecimal> stages,
            Map<String, String> parameters) {
        var rows =
                jdbc.queryForList(
                        """
                        select t.*, fv.value factor_value, fv.approved factor_approved,
                               f.factor_code
                        from transport_activity t
                        left join factor_version fv on fv.id = t.factor_version_id
                        left join emission_factor f on f.id = fv.factor_id
                        where t.product_version_id = ?
                        """,
                        productVersionId);
        if (rows.isEmpty()) {
            errors.add(
                    Map.of(
                            "code", "INBOUND_TRANSPORT_MISSING",
                            "message",
                                    "At least one approved inbound transport activity is required"));
            return List.of();
        }
        var payload = new ArrayList<Map<String, Object>>();
        var index = 0;
        for (var item : rows) {
            index++;
            if (!Boolean.TRUE.equals(item.get("approved"))) {
                errors.add(Map.of("code", "TRANSPORT_NOT_APPROVED", "id", item.get("id")));
            }
            if (!Boolean.TRUE.equals(item.get("factor_approved"))) {
                errors.add(Map.of("code", "TRANSPORT_FACTOR_NOT_APPROVED", "id", item.get("id")));
                continue;
            }
            var distance = decimal(item.get("distance_km"));
            var mass = decimal(item.get("mass_kg"));
            var tkm = mass.divide(new BigDecimal("1000")).multiply(distance);
            stages.merge(
                    "inbound_transport",
                    tkm.multiply(decimal(item.get("factor_value"))),
                    BigDecimal::add);
            parameters.put("transport_" + index + "_tkm", plain(tkm));
            var row = new LinkedHashMap<String, Object>();
            row.put("mode", item.get("mode"));
            row.put("distance_km", plain(distance));
            row.put("mass_kg", plain(mass));
            row.put(
                    "load_factor",
                    item.get("load_factor") == null
                            ? null
                            : plain(decimal(item.get("load_factor"))));
            row.put("factor_code", item.get("factor_code"));
            row.put("factor_value", plain(decimal(item.get("factor_value"))));
            row.put("material_code", null);
            row.put("source", item.get("source"));
            payload.add(row);
        }
        return payload;
    }

    private Map<String, Object> one(String sql, Object... args) {
        var rows = jdbc.queryForList(sql, args);
        return rows.isEmpty() ? null : rows.getFirst();
    }

    private static LinkedHashMap<String, BigDecimal> stageMap() {
        var stages = new LinkedHashMap<String, BigDecimal>();
        stages.put("raw_materials", ZERO);
        stages.put("inbound_transport", ZERO);
        stages.put("manufacturing", ZERO);
        stages.put("packaging", ZERO);
        return stages;
    }

    private static BigDecimal decimal(Object value) {
        return value instanceof BigDecimal decimal
                ? decimal
                : new BigDecimal(String.valueOf(value));
    }

    private static String plain(BigDecimal value) {
        return value.stripTrailingZeros().toPlainString();
    }
}
