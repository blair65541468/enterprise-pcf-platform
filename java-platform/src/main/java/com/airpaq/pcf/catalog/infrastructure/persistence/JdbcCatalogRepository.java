package com.airpaq.pcf.catalog.infrastructure.persistence;

import com.airpaq.pcf.audit.application.AuditService;
import com.airpaq.pcf.catalog.api.dto.FactorApproval;
import com.airpaq.pcf.catalog.api.dto.MappingCreate;
import com.airpaq.pcf.catalog.api.dto.ModelTemplateCreate;
import com.airpaq.pcf.catalog.api.dto.TransportCreate;
import com.airpaq.pcf.catalog.application.CatalogOperations;
import com.airpaq.pcf.shared.json.CanonicalJson;
import com.airpaq.pcf.shared.json.JsonSupport;
import com.airpaq.pcf.shared.web.DomainException;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class JdbcCatalogRepository implements CatalogOperations {

    private final JdbcTemplate jdbc;
    private final AuditService audit;
    private final CanonicalJson canonicalJson;
    private final JsonSupport json;

    public JdbcCatalogRepository(
            JdbcTemplate jdbc, AuditService audit, CanonicalJson canonicalJson, JsonSupport json) {
        this.jdbc = jdbc;
        this.audit = audit;
        this.canonicalJson = canonicalJson;
        this.json = json;
    }

    @Transactional
    public Map<String, Object> approveFactor(
            String factorCode, FactorApproval request, String actor) {
        var version =
                one(
                        """
                        select v.* from factor_version v
                        join emission_factor f on f.id = v.factor_id
                        where f.factor_code = ? order by v.version desc limit 1
                        """,
                        factorCode,
                        "Factor not found");
        if (Boolean.TRUE.equals(version.get("approved"))) {
            throw new DomainException(
                    409, "Approved factor versions are immutable; import a new factor version");
        }
        var density =
                request.densityKgM3() == null
                        ? version.get("density_kg_m3")
                        : request.densityKgM3();
        var licence =
                request.licenceRef() == null ? version.get("licence_ref") : request.licenceRef();
        var content = new LinkedHashMap<String, Object>();
        content.put("value", String.valueOf(version.get("value")));
        content.put("activity_unit", version.get("activity_unit"));
        content.put("co2e_unit", version.get("co2e_unit"));
        content.put("source", version.get("source"));
        content.put("standard", version.get("standard"));
        content.put("region", version.get("region"));
        content.put("reference_year", version.get("reference_year"));
        content.put("data_quality", version.get("data_quality"));
        content.put("density_kg_m3", density == null ? null : String.valueOf(density));
        content.put("licence_ref", licence);
        jdbc.update(
                """
                update factor_version set density_kg_m3 = ?, licence_ref = ?,
                  content_hash = ?, approved = true where id = ?
                """,
                density,
                licence,
                canonicalJson.sha256(content),
                version.get("id"));
        audit.record(
                actor,
                "factor.approved",
                "factor_version",
                String.valueOf(version.get("id")),
                null,
                canonicalJson.sha256(
                        Map.of(
                                "value", String.valueOf(version.get("value")),
                                "unit", String.valueOf(version.get("activity_unit")),
                                "density", density == null ? "" : String.valueOf(density))),
                Map.of());
        return Map.of(
                "factor_code", factorCode, "version", version.get("version"), "approved", true);
    }

    @Transactional
    public Map<String, Object> createMapping(MappingCreate request, String actor) {
        var material =
                one(
                        "select id from material where code = ?",
                        request.materialCode(),
                        "Material not found");
        var id = UUID.randomUUID().toString();
        jdbc.update(
                """
                insert into material_process_mapping
                  (id, material_id, process_uuid, reference_flow_uuid, openlca_unit,
                   conversion_rule, region, reference_year, database_version,
                   status, reviewed_by, created_at)
                values (?, ?, ?, ?, ?, ?::json, ?, ?, ?, 'approved', ?, ?)
                """,
                id,
                material.get("id"),
                request.processUuid(),
                request.referenceFlowUuid(),
                request.openlcaUnit(),
                json.write(request.conversionRule()),
                request.region(),
                request.referenceYear(),
                request.databaseVersion(),
                actor,
                java.sql.Timestamp.from(Instant.now()));
        audit.record(
                actor,
                "material_mapping.approved",
                "material_process_mapping",
                id,
                null,
                null,
                json.map(json.write(request)));
        return Map.of("id", id, "status", "approved");
    }

    @Transactional
    public Map<String, Object> createTransport(String sku, TransportCreate request, String actor) {
        var productVersion =
                one(
                        """
                        select v.id from product_version v join product p on p.id = v.product_id
                        where p.sku = ? order by v.version desc limit 1
                        """,
                        sku,
                        "Product or factor not found");
        var factor =
                one(
                        """
                        select v.* from factor_version v
                        join emission_factor f on f.id = v.factor_id
                        where f.factor_code = ? order by v.version desc limit 1
                        """,
                        request.factorCode(),
                        "Product or factor not found");
        if (!Boolean.TRUE.equals(factor.get("approved"))) {
            throw new DomainException(409, "Transport factor must be approved");
        }
        var id = UUID.randomUUID().toString();
        jdbc.update(
                """
                insert into transport_activity
                  (id, product_version_id, mode, distance_km, mass_kg, load_factor,
                   factor_version_id, source, approved, created_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, true, ?)
                """,
                id,
                productVersion.get("id"),
                request.mode(),
                request.distanceKm(),
                request.massKg(),
                request.loadFactor(),
                factor.get("id"),
                request.source(),
                java.sql.Timestamp.from(Instant.now()));
        audit.record(
                actor,
                "transport_activity.approved",
                "transport_activity",
                id,
                null,
                null,
                json.map(json.write(request)));
        return Map.of("id", id, "approved", true);
    }

    @Transactional
    public Map<String, Object> approveRoute(String sku, String routeVersion, String actor) {
        var route =
                one(
                        """
                        select r.id from process_route r join product p on p.id = r.product_id
                        where p.sku = ? and r.version = ?
                        """,
                        sku,
                        routeVersion,
                        "Route not found");
        jdbc.update("update process_route set approved = true where id = ?", route.get("id"));
        audit.record(
                actor,
                "route.approved",
                "process_route",
                String.valueOf(route.get("id")),
                null,
                null,
                Map.of("sku", sku, "version", routeVersion));
        return Map.of("id", route.get("id"), "approved", true);
    }

    @Transactional
    public Map<String, Object> createTemplate(ModelTemplateCreate request, String actor) {
        var templates =
                jdbc.queryForList("select id from model_template where code = ?", request.code());
        var templateId =
                templates.isEmpty()
                        ? UUID.randomUUID().toString()
                        : String.valueOf(templates.getFirst().get("id"));
        if (templates.isEmpty()) {
            jdbc.update(
                    """
                    insert into model_template
                      (id, code, name, product_family, created_at)
                    values (?, ?, ?, ?, ?)
                    """,
                    templateId,
                    request.code(),
                    request.name(),
                    request.productFamily(),
                    java.sql.Timestamp.from(Instant.now()));
        }
        if (!jdbc.queryForList(
                        """
                                select id from model_template_version
                                where template_id = ? and version = ?
                                """,
                        templateId,
                        request.version())
                .isEmpty()) {
            throw new DomainException(409, "Template version already exists");
        }
        var id = UUID.randomUUID().toString();
        jdbc.update(
                """
                insert into model_template_version
                  (id, template_id, version, product_system_uuid, impact_method_uuid,
                   database_version, parameter_schema, approved, created_at)
                values (?, ?, ?, ?, ?, ?, ?::json, true, ?)
                """,
                id,
                templateId,
                request.version(),
                request.productSystemUuid(),
                request.impactMethodUuid(),
                request.databaseVersion(),
                json.write(request.parameterSchema()),
                java.sql.Timestamp.from(Instant.now()));
        audit.record(
                actor,
                "model_template.approved",
                "model_template_version",
                id,
                null,
                null,
                json.map(json.write(request)));
        return Map.of("id", id, "version", request.version(), "approved", true);
    }

    private Map<String, Object> one(String sql, Object value, String message) {
        var rows = jdbc.queryForList(sql, value);
        if (rows.isEmpty()) throw new DomainException(404, message);
        return rows.getFirst();
    }

    private Map<String, Object> one(String sql, Object first, Object second, String message) {
        var rows = jdbc.queryForList(sql, first, second);
        if (rows.isEmpty()) throw new DomainException(404, message);
        return rows.getFirst();
    }
}
