package com.airpaq.pcf.calculations;

import static com.airpaq.pcf.infrastructure.api.ApiContracts.CalculationStatus;

import com.airpaq.pcf.audit.AuditService;
import com.airpaq.pcf.infrastructure.api.ApiContracts.CalculationCreate;
import com.airpaq.pcf.infrastructure.api.ApiContracts.CalculationOut;
import com.airpaq.pcf.infrastructure.api.ApiContracts.ContributionOut;
import com.airpaq.pcf.infrastructure.api.ApiContracts.ResultSummaryOut;
import com.airpaq.pcf.infrastructure.config.PcfProperties;
import com.airpaq.pcf.infrastructure.json.CanonicalJson;
import com.airpaq.pcf.infrastructure.json.JsonSupport;
import com.airpaq.pcf.infrastructure.storage.ObjectStorage;
import com.airpaq.pcf.infrastructure.web.DomainException;
import java.math.BigDecimal;
import java.sql.Timestamp;
import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CalculationService {

    private final JdbcTemplate jdbc;
    private final JsonSupport json;
    private final CanonicalJson canonicalJson;
    private final AuditService audit;
    private final CalculationEngine engine;
    private final ObjectStorage storage;
    private final PcfProperties properties;
    private final Clock clock = Clock.systemUTC();

    public CalculationService(
            JdbcTemplate jdbc,
            JsonSupport json,
            CanonicalJson canonicalJson,
            AuditService audit,
            CalculationEngine engine,
            ObjectStorage storage,
            PcfProperties properties) {
        this.jdbc = jdbc;
        this.json = json;
        this.canonicalJson = canonicalJson;
        this.audit = audit;
        this.engine = engine;
        this.storage = storage;
        this.properties = properties;
    }

    @Transactional
    public CalculationOut create(CalculationCreate request, String actor, String requestId) {
        var product =
                one("select id from product where sku = ?", request.sku(), "Product not found");
        var snapshot =
                one(
                        """
                        select * from calculation_snapshot
                        where product_id = ? and version = ?
                        """,
                        product.get("id"),
                        request.snapshotVersion(),
                        "Snapshot not found");
        var snapshotPayload = json.map(snapshot.get("payload"));
        if (!request.factorSetVersion().equals(snapshot.get("factor_set_version"))) {
            throw new DomainException(409, "Factor set does not match frozen snapshot");
        }
        if (!request.routeVersion().equals(snapshotPayload.get("route_version"))) {
            throw new DomainException(409, "Route version does not match frozen snapshot");
        }
        if (!request.boundary().equals(snapshot.get("boundary"))) {
            throw new DomainException(409, "Boundary does not match frozen snapshot");
        }
        var requestHash = canonicalJson.sha256(request);
        var existing =
                jdbc.queryForList(
                        "select id, request_hash from calculation_run where idempotency_key = ?",
                        request.idempotencyKey());
        if (!existing.isEmpty()) {
            var row = existing.getFirst();
            if (row.get("request_hash") != null && !requestHash.equals(row.get("request_hash"))) {
                throw new DomainException(
                        409,
                        "Idempotency key was already used for a different calculation request");
            }
            return get(String.valueOf(row.get("id")));
        }
        var template =
                one(
                        """
                        select v.* from model_template_version v
                        join model_template t on t.id = v.template_id
                        where v.version = ?
                        """,
                        request.modelTemplateVersion(),
                        "Model template version not found: " + request.modelTemplateVersion());
        if (!Boolean.TRUE.equals(template.get("approved"))) {
            throw new DomainException(
                    422,
                    "Model template version is not approved: " + request.modelTemplateVersion());
        }
        var id = UUID.randomUUID().toString();
        var eventId = UUID.randomUUID().toString();
        var occurredAt = Instant.now(clock);
        var now = java.sql.Timestamp.from(occurredAt);
        try {
            jdbc.update(
                    """
                    insert into calculation_run
                      (id, snapshot_id, product_id, model_template_version_id,
                       idempotency_key, request_hash, status, impact_method,
                       requested_by, engine, attempt_count, created_at)
                    values (?, ?, ?, ?, ?, ?, 'queued', ?,
                            ?, ?, 0, ?)
                    """,
                    id,
                    snapshot.get("id"),
                    product.get("id"),
                    template.get("id"),
                    request.idempotencyKey(),
                    requestHash,
                    request.impactMethod(),
                    actor,
                    engine.name(),
                    now);
            jdbc.update(
                    """
                    insert into outbox_event
                      (id, event_type, aggregate_type, aggregate_id, payload,
                       attempt_count, created_at)
                    values (?, 'calculation.requested', 'calculation_run', ?,
                            ?::json, 0, ?)
                    """,
                    eventId,
                    id,
                    json.write(
                            Map.of(
                                    "schemaVersion",
                                    1,
                                    "eventId",
                                    eventId,
                                    "runId",
                                    id,
                                    "requestId",
                                    requestId == null ? "" : requestId,
                                    "occurredAt",
                                    occurredAt.toString())),
                    now);
        } catch (DuplicateKeyException exception) {
            return create(request, actor, requestId);
        }
        audit.record(
                actor,
                "calculation.queued",
                "calculation_run",
                id,
                null,
                null,
                Map.of(
                        "snapshot_id", snapshot.get("id"),
                        "idempotency_key", request.idempotencyKey()));
        return get(id);
    }

    public CalculationOut get(String runId) {
        var run = one("select * from calculation_run where id = ?", runId, "Calculation not found");
        var summaries = jdbc.queryForList("select * from result_summary where run_id = ?", runId);
        return toOut(run, summaries.isEmpty() ? null : summaries.getFirst());
    }

    public List<ContributionOut> contributions(String runId) {
        get(runId);
        return jdbc
                .queryForList(
                        """
                        select * from result_contribution
                        where run_id = ? order by rank nulls last, created_at
                        """,
                        runId)
                .stream()
                .map(
                        row ->
                                new ContributionOut(
                                        text(row, "dimension"),
                                        text(row, "code"),
                                        text(row, "name"),
                                        decimal(row, "amount_kg_co2e"),
                                        row.get("rank") == null
                                                ? null
                                                : ((Number) row.get("rank")).intValue(),
                                        json.map(row.get("metadata_json"))))
                .toList();
    }

    @Transactional
    public CalculationOut submit(String runId, String actor) {
        var run = lockedRun(runId);
        requireStatus(run, "calculated", "Only calculated runs can be submitted");
        var now = java.sql.Timestamp.from(Instant.now(clock));
        jdbc.update(
                """
                update calculation_run set status = 'submitted',
                  submitted_by = ?, submitted_at = ? where id = ?
                """,
                actor,
                now,
                runId);
        audit.record(
                actor,
                "calculation.submitted",
                "calculation_run",
                runId,
                text(run, "manifest_hash"),
                text(run, "manifest_hash"),
                Map.of());
        return get(runId);
    }

    @Transactional
    public CalculationOut approve(String runId, String actor) {
        var run = lockedRun(runId);
        requireStatus(run, "submitted", "Only submitted runs can be approved");
        if (actor.equals(run.get("submitted_by"))) {
            throw new DomainException(409, "Four-eyes rule: submitter cannot approve the same run");
        }
        jdbc.queryForList("select id from product where id = ? for update", run.get("product_id"));
        var previous =
                jdbc.queryForList(
                        """
                        select id, manifest_hash from calculation_run
                        where product_id = ? and status = 'approved' and id <> ?
                        for update
                        """,
                        run.get("product_id"),
                        runId);
        for (var item : previous) {
            jdbc.update(
                    "update calculation_run set status = 'superseded' where id = ?",
                    item.get("id"));
            audit.record(
                    actor,
                    "calculation.superseded",
                    "calculation_run",
                    text(item, "id"),
                    text(item, "manifest_hash"),
                    text(item, "manifest_hash"),
                    Map.of("replacement_run_id", runId));
        }
        jdbc.update(
                """
                update calculation_run set status = 'approved',
                  approved_by = ?, approved_at = ? where id = ?
                """,
                actor,
                java.sql.Timestamp.from(Instant.now(clock)),
                runId);
        audit.record(
                actor,
                "calculation.approved",
                "calculation_run",
                runId,
                text(run, "manifest_hash"),
                text(run, "manifest_hash"),
                Map.of(
                        "superseded_run_ids",
                        previous.stream().map(item -> item.get("id")).toList()));
        return get(runId);
    }

    @Transactional
    public CalculationOut reject(String runId, String actor, String reason) {
        var run = lockedRun(runId);
        requireStatus(run, "submitted", "Only submitted runs can be rejected");
        if (actor.equals(run.get("submitted_by"))) {
            throw new DomainException(409, "Four-eyes rule: submitter cannot reject the same run");
        }
        jdbc.update(
                """
                update calculation_run set status = 'rejected',
                  approved_by = ?, rejection_reason = ? where id = ?
                """,
                actor,
                reason,
                runId);
        audit.record(
                actor,
                "calculation.rejected",
                "calculation_run",
                runId,
                null,
                null,
                Map.of("reason", reason));
        return get(runId);
    }

    @Transactional
    public boolean execute(String runId) {
        var token = UUID.randomUUID().toString();
        var now = java.sql.Timestamp.from(Instant.now(clock));
        var claimed =
                jdbc.update(
                        """
                        update calculation_run set status = 'calculating',
                          execution_token = ?, attempt_count = attempt_count + 1,
                          heartbeat_at = ?, started_at = ?, completed_at = null, error = null
                        where id = ? and status = 'queued'
                        """,
                        token,
                        now,
                        now,
                        runId);
        if (claimed == 0) return false;
        try {
            calculateClaimed(runId, token);
            return true;
        } catch (RuntimeException exception) {
            jdbc.update(
                    """
                    update calculation_run set status = 'failed', execution_token = null,
                      error = ?, completed_at = ? where id = ? and execution_token = ?
                    """,
                    truncate(exception.getMessage()),
                    java.sql.Timestamp.from(Instant.now(clock)),
                    runId,
                    token);
            audit.record(
                    "pcf-worker",
                    "calculation.failed",
                    "calculation_run",
                    runId,
                    null,
                    null,
                    Map.of("error", truncate(exception.getMessage())));
            throw exception;
        }
    }

    @Transactional
    public boolean retry(String runId, RuntimeException exception) {
        var rows =
                jdbc.queryForList(
                        "select attempt_count from calculation_run where id = ? for update", runId);
        if (rows.isEmpty()) return false;
        var attempts = ((Number) rows.getFirst().get("attempt_count")).intValue();
        var canRetry = attempts < properties.calculation().maxAttempts();
        jdbc.update(
                """
                update calculation_run set status = ?::calculationstatus,
                  execution_token = null, error = ?, completed_at = ?
                where id = ?
                """,
                canRetry ? "queued" : "failed",
                truncate(exception.getMessage()),
                canRetry ? null : java.sql.Timestamp.from(Instant.now(clock)),
                runId);
        audit.record(
                "pcf-worker",
                canRetry ? "calculation.retry_scheduled" : "calculation.failed",
                "calculation_run",
                runId,
                null,
                null,
                Map.of("error", truncate(exception.getMessage()), "attempt_count", attempts));
        return canRetry;
    }

    @Transactional
    public int recoverStale() {
        var cutoff =
                java.sql.Timestamp.from(
                        Instant.now(clock).minus(properties.calculation().staleAfter()));
        var stale =
                jdbc.queryForList(
                        """
                        select id from calculation_run
                        where status = 'calculating' and heartbeat_at < ?
                        for update skip locked
                        """,
                        cutoff);
        for (var row : stale) {
            jdbc.update(
                    """
                    update calculation_run set status = 'queued',
                      execution_token = null, error = 'Recovered stale calculation'
                    where id = ?
                    """,
                    row.get("id"));
        }
        return stale.size();
    }

    private void calculateClaimed(String runId, String token) {
        var run = one("select * from calculation_run where id = ?", runId, "Calculation not found");
        var snapshot =
                one(
                        "select * from calculation_snapshot where id = ?",
                        run.get("snapshot_id"),
                        "Snapshot not found");
        var template =
                one(
                        "select * from model_template_version where id = ?",
                        run.get("model_template_version_id"),
                        "Model template not found");
        var payload = json.map(snapshot.get("payload"));
        var schema = json.map(template.get("parameter_schema"));
        var contexts = mapOfMaps(schema.get("contexts"));
        var groups = mapOfLists(schema.get("stage_process_uuids"));
        var result =
                engine.calculate(
                        new CalculationEngine.EngineInput(payload, text(run, "impact_method")),
                        new CalculationEngine.ModelTemplateConfig(
                                text(template, "product_system_uuid"),
                                text(template, "impact_method_uuid"),
                                text(template, "database_version"),
                                schema,
                                contexts,
                                groups));
        assertConsistent(result);
        var raw = rawResult(result);
        var bytes = canonicalJson.bytes(raw);
        var key = "calculations/" + runId + "/openlca-result.json";
        storage.put(key, bytes, "application/json");
        if (!CanonicalJson.sha256(bytes).equals(CanonicalJson.sha256(storage.get(key)))) {
            throw new IllegalStateException("Stored openLCA result failed SHA-256 verification");
        }
        jdbc.update("delete from result_contribution where run_id = ?", runId);
        jdbc.update("delete from result_summary where run_id = ?", runId);
        var iso = result.isoCategories();
        var stages = result.stages();
        jdbc.update(
                """
                insert into result_summary
                  (id, run_id, total_kg_co2e, functional_unit, boundary, impact_method,
                   aircraft, biogenic_emissions, biogenic_removals, fossil,
                   land_use_change, raw_materials, inbound_transport, manufacturing,
                   packaging, data_quality_status, created_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                UUID.randomUUID().toString(),
                runId,
                result.totalKgCo2e(),
                String.valueOf(payload.get("functional_unit")),
                snapshot.get("boundary"),
                run.get("impact_method"),
                value(iso, "aircraft"),
                value(iso, "biogenic_emissions"),
                value(iso, "biogenic_removals"),
                value(iso, "fossil"),
                value(iso, "land_use_change"),
                value(stages, "raw_materials"),
                value(stages, "inbound_transport"),
                value(stages, "manufacturing"),
                value(stages, "packaging"),
                engine.name().equals("mock") ? "integration_test" : "validated",
                java.sql.Timestamp.from(Instant.now(clock)));
        var rank = 0;
        for (var contribution : result.contributions()) {
            jdbc.update(
                    """
                    insert into result_contribution
                      (id, run_id, dimension, code, name, amount_kg_co2e,
                       rank, metadata_json, created_at)
                    values (?, ?, ?, ?, ?, ?, ?, ?::json, ?)
                    """,
                    UUID.randomUUID().toString(),
                    runId,
                    contribution.dimension(),
                    contribution.code(),
                    contribution.name(),
                    contribution.amountKgCo2e(),
                    ++rank,
                    json.write(contribution.metadata()),
                    java.sql.Timestamp.from(Instant.now(clock)));
        }
        var manifest = new LinkedHashMap<String, Object>();
        manifest.put("snapshot_manifest_hash", snapshot.get("manifest_hash"));
        manifest.put("template_version", template.get("version"));
        manifest.put("template_database_version", template.get("database_version"));
        manifest.put("impact_method", run.get("impact_method"));
        manifest.put("engine", engine.name());
        manifest.put("engine_version", result.engineVersion());
        manifest.put("app_version", properties.appVersion());
        manifest.put("git_commit", properties.gitCommit());
        manifest.put("raw_result_sha256", canonicalJson.sha256(raw));
        manifest.put("result_total", result.totalKgCo2e().toPlainString());
        var manifestHash = canonicalJson.sha256(manifest);
        var completed = java.sql.Timestamp.from(Instant.now(clock));
        var updated =
                jdbc.update(
                        """
                        update calculation_run set status = 'calculated',
                          engine = ?, engine_version = ?, raw_result_object_key = ?,
                          completed_at = ?, heartbeat_at = ?, execution_token = null,
                          manifest_hash = ?
                        where id = ? and execution_token = ?
                        """,
                        engine.name(),
                        result.engineVersion(),
                        key,
                        completed,
                        completed,
                        manifestHash,
                        runId,
                        token);
        if (updated != 1) {
            throw new IllegalStateException("Calculation execution token was lost");
        }
        audit.record(
                "pcf-worker",
                "calculation.completed",
                "calculation_run",
                runId,
                null,
                manifestHash,
                manifest);
    }

    public List<Map<String, Object>> auditEvents(String runId) {
        get(runId);
        return jdbc
                .queryForList(
                        """
                        select id, occurred_at, actor, action, before_hash,
                          after_hash, details from audit_event
                        where object_id = ? order by occurred_at
                        """,
                        runId)
                .stream()
                .map(
                        row -> {
                            Map<String, Object> result = new LinkedHashMap<>();
                            result.put("id", row.get("id"));
                            result.put("occurred_at", instant(row.get("occurred_at")));
                            result.put("actor", row.get("actor"));
                            result.put("action", row.get("action"));
                            result.put("before_hash", row.get("before_hash"));
                            result.put("after_hash", row.get("after_hash"));
                            result.put("details", json.map(row.get("details")));
                            return result;
                        })
                .toList();
    }

    Map<String, Object> rawRun(String runId) {
        return one("select * from calculation_run where id = ?", runId, "Calculation not found");
    }

    private Map<String, Object> lockedRun(String runId) {
        return one(
                "select * from calculation_run where id = ? for update",
                runId,
                "Calculation not found");
    }

    private Map<String, Object> one(String sql, Object value, String notFound) {
        var rows = jdbc.queryForList(sql, value);
        if (rows.isEmpty()) throw new DomainException(404, notFound);
        return rows.getFirst();
    }

    private Map<String, Object> one(String sql, Object first, Object second, String notFound) {
        var rows = jdbc.queryForList(sql, first, second);
        if (rows.isEmpty()) throw new DomainException(404, notFound);
        return rows.getFirst();
    }

    private CalculationOut toOut(Map<String, Object> run, Map<String, Object> summary) {
        return new CalculationOut(
                text(run, "id"),
                CalculationStatus.valueOf(text(run, "status")),
                text(run, "idempotency_key"),
                text(run, "impact_method"),
                text(run, "engine"),
                text(run, "error"),
                text(run, "manifest_hash"),
                instant(run.get("created_at")),
                summary == null
                        ? null
                        : new ResultSummaryOut(
                                decimal(summary, "total_kg_co2e"),
                                text(summary, "functional_unit"),
                                text(summary, "boundary"),
                                text(summary, "impact_method"),
                                decimal(summary, "aircraft"),
                                decimal(summary, "biogenic_emissions"),
                                decimal(summary, "biogenic_removals"),
                                decimal(summary, "fossil"),
                                decimal(summary, "land_use_change"),
                                decimal(summary, "raw_materials"),
                                decimal(summary, "inbound_transport"),
                                decimal(summary, "manufacturing"),
                                decimal(summary, "packaging"),
                                text(summary, "data_quality_status")));
    }

    private static void requireStatus(Map<String, Object> run, String expected, String message) {
        if (!expected.equals(String.valueOf(run.get("status")))) {
            throw new DomainException(409, message);
        }
    }

    private static void assertConsistent(CalculationEngine.EngineResult result) {
        var tolerance =
                result.totalKgCo2e()
                        .abs()
                        .multiply(new BigDecimal("0.001"))
                        .max(new BigDecimal("0.01"));
        var stageTotal = result.stages().values().stream().reduce(BigDecimal.ZERO, BigDecimal::add);
        if (stageTotal.subtract(result.totalKgCo2e()).abs().compareTo(tolerance) > 0) {
            throw new IllegalStateException(
                    "Lifecycle stage contributions do not reconcile with the openLCA total");
        }
        var isoTotal =
                result.isoCategories().values().stream().reduce(BigDecimal.ZERO, BigDecimal::add);
        if (isoTotal.subtract(result.totalKgCo2e()).abs().compareTo(tolerance) > 0) {
            throw new IllegalStateException(
                    "ISO 14067 category contributions do not reconcile with the openLCA total");
        }
    }

    private static Map<String, Object> rawResult(CalculationEngine.EngineResult result) {
        var raw = new LinkedHashMap<String, Object>();
        raw.put("engine_version", result.engineVersion());
        raw.put("total_kg_co2e", result.totalKgCo2e().toPlainString());
        raw.put("iso_categories", stringify(result.isoCategories()));
        raw.put("stages", stringify(result.stages()));
        var contributions = new ArrayList<Map<String, Object>>();
        for (var item : result.contributions()) {
            contributions.add(
                    Map.of(
                            "dimension", item.dimension(),
                            "code", item.code(),
                            "name", item.name(),
                            "amount_kg_co2e", item.amountKgCo2e().toPlainString(),
                            "metadata", item.metadata()));
        }
        raw.put("contributions", contributions);
        raw.put("raw", result.raw());
        return raw;
    }

    private static Map<String, String> stringify(Map<String, BigDecimal> values) {
        var result = new LinkedHashMap<String, String>();
        values.forEach((key, value) -> result.put(key, value.toPlainString()));
        return result;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Map<String, Object>> mapOfMaps(Object value) {
        return value instanceof Map<?, ?> map ? (Map<String, Map<String, Object>>) map : Map.of();
    }

    @SuppressWarnings("unchecked")
    private static Map<String, List<String>> mapOfLists(Object value) {
        return value instanceof Map<?, ?> map ? (Map<String, List<String>>) map : Map.of();
    }

    private static BigDecimal value(Map<String, BigDecimal> values, String key) {
        return values.getOrDefault(key, BigDecimal.ZERO);
    }

    private static BigDecimal decimal(Map<String, Object> row, String key) {
        var value = row.get(key);
        return value == null ? BigDecimal.ZERO : new BigDecimal(String.valueOf(value));
    }

    private static String text(Map<String, Object> row, String key) {
        var value = row.get(key);
        return value == null ? null : String.valueOf(value);
    }

    private static Instant instant(Object value) {
        if (value == null) return null;
        if (value instanceof Instant result) return result;
        if (value instanceof Timestamp timestamp) return timestamp.toInstant();
        return Instant.parse(String.valueOf(value));
    }

    private static String truncate(String value) {
        if (value == null) return "Calculation failed";
        return value.length() <= 4000 ? value : value.substring(0, 4000);
    }
}
