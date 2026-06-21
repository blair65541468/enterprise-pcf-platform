package com.airpaq.pcf.imports.infrastructure.excel;

import com.airpaq.pcf.audit.application.AuditService;
import com.airpaq.pcf.imports.api.dto.ImportIssueOut;
import com.airpaq.pcf.imports.api.dto.ImportJobOut;
import com.airpaq.pcf.imports.api.dto.ImportStatus;
import com.airpaq.pcf.imports.application.ImportOperations;
import com.airpaq.pcf.shared.json.CanonicalJson;
import com.airpaq.pcf.shared.json.JsonSupport;
import com.airpaq.pcf.shared.storage.ObjectStorage;
import com.airpaq.pcf.shared.web.DomainException;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.multipart.MultipartFile;

@Service
public class ExcelImportAdapter implements ImportOperations {

    private final JdbcTemplate jdbc;
    private final ObjectStorage storage;
    private final CanonicalJson canonicalJson;
    private final JsonSupport json;
    private final AuditService audit;
    private final ExcelFileParser parser;
    private final ExcelFileTypeDetector typeDetector;
    private final TransactionTemplate transaction;
    private final TransactionTemplate requiresNew;

    public ExcelImportAdapter(
            JdbcTemplate jdbc,
            ObjectStorage storage,
            CanonicalJson canonicalJson,
            JsonSupport json,
            AuditService audit,
            ExcelFileParser parser,
            ExcelFileTypeDetector typeDetector,
            PlatformTransactionManager transactionManager) {
        this.jdbc = jdbc;
        this.storage = storage;
        this.canonicalJson = canonicalJson;
        this.json = json;
        this.audit = audit;
        this.parser = parser;
        this.typeDetector = typeDetector;
        this.transaction = new TransactionTemplate(transactionManager);
        this.requiresNew = new TransactionTemplate(transactionManager);
        this.requiresNew.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
    }

    public ImportJobOut importFiles(List<MultipartFile> files, String actor) {
        if (files == null || files.isEmpty()) {
            throw new DomainException(400, "At least one XLSX file is required");
        }
        for (var file : files) {
            var name = file.getOriginalFilename();
            if (name == null || !name.toLowerCase().endsWith(".xlsx")) {
                throw new DomainException(400, "Unsupported file: " + name);
            }
        }
        var jobId = UUID.randomUUID().toString();
        var manifest = new ArrayList<Map<String, Object>>();
        try {
            return transaction.execute(ignored -> process(jobId, files, actor, manifest));
        } catch (RuntimeException exception) {
            requiresNew.executeWithoutResult(
                    ignored -> persistFailure(jobId, actor, manifest, rootMessage(exception)));
            throw new DomainException(422, rootMessage(exception));
        }
    }

    private ImportJobOut process(
            String jobId,
            List<MultipartFile> files,
            String actor,
            List<Map<String, Object>> manifest) {
        var createdAt = java.sql.Timestamp.from(Instant.now());
        jdbc.update(
                """
                insert into import_job
                  (id, status, created_by, file_manifest, summary, created_at)
                values (?, 'processing', ?, '[]'::json, '{}'::json, ?)
                """,
                jobId,
                actor,
                createdAt);
        var parsed = new ArrayList<ParsedFile>();
        for (var file : files) {
            try {
                var content = file.getBytes();
                var sha256 = CanonicalJson.sha256(content);
                var name = file.getOriginalFilename();
                var key = "imports/" + jobId + "/" + sha256 + "-" + name;
                storage.put(
                        key,
                        content,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
                if (!sha256.equals(CanonicalJson.sha256(storage.get(key)))) {
                    throw new IllegalStateException(
                            "Stored import failed SHA-256 verification: " + name);
                }
                var parsedFile = parser.parse(name, content);
                parsed.add(parsedFile);
                manifest.add(
                        Map.of(
                                "file_name", name,
                                "sha256", sha256,
                                "object_key", key,
                                "rows", parsedFile.rows().size()));
                if (!parsedFile.duplicateHeaders().isEmpty()) {
                    issue(
                            jobId,
                            "warning",
                            name,
                            null,
                            null,
                            "DUPLICATE_HEADERS",
                            "Duplicate headers were renamed during import: "
                                    + parsedFile.duplicateHeaders());
                }
            } catch (Exception exception) {
                throw new IllegalArgumentException(
                        "Unable to parse XLSX file: " + file.getOriginalFilename(), exception);
            }
        }
        jdbc.update(
                "update import_job set file_manifest = ?::json where id = ?",
                json.write(manifest),
                jobId);
        var counts = new LinkedHashMap<String, Integer>();
        for (var file : parsed) {
            if (typeDetector.detect(file) == ExcelFileType.FACTOR) {
                importFactors(jobId, file, counts);
            }
        }
        for (var file : parsed) {
            if (typeDetector.detect(file) == ExcelFileType.PRODUCT) {
                importProducts(jobId, file, counts);
            }
        }
        for (var file : parsed) {
            switch (typeDetector.detect(file)) {
                case BOM -> importBom(jobId, file, counts);
                case ROUTE -> importRoute(jobId, file, counts);
                case EQUIPMENT -> importEquipment(file, counts);
                case SUPPLIER -> importSuppliers(file, counts);
                case CAPABILITY_BASELINE -> scanTestRecords(jobId, file);
                default -> {
                    // Factor and product files were handled in dependency order above.
                }
            }
        }
        var errors =
                jdbc.queryForObject(
                        """
                        select count(*) from import_issue
                        where import_job_id = ? and severity = 'error'
                        """,
                        Integer.class,
                        jobId);
        var status = errors != null && errors > 0 ? "failed" : "validated";
        var completed = java.sql.Timestamp.from(Instant.now());
        jdbc.update(
                """
                update import_job set status = ?::importstatus, summary = ?::json,
                  completed_at = ? where id = ?
                """,
                status,
                json.write(counts),
                completed,
                jobId);
        audit.record(
                actor,
                "import.completed",
                "import_job",
                jobId,
                null,
                canonicalJson.sha256(Map.of("manifest", manifest, "summary", counts)),
                Map.of("status", status));
        return get(jobId);
    }

    public ImportJobOut get(String jobId) {
        var jobs = jdbc.queryForList("select * from import_job where id = ?", jobId);
        if (jobs.isEmpty()) throw new DomainException(404, "Import job not found");
        var row = jobs.getFirst();
        var issues =
                jdbc
                        .queryForList(
                                """
                                select * from import_issue
                                where import_job_id = ? order by created_at
                                """,
                                jobId)
                        .stream()
                        .map(
                                issue ->
                                        new ImportIssueOut(
                                                text(issue, "severity"),
                                                text(issue, "file_name"),
                                                integer(issue.get("row_number")),
                                                text(issue, "field"),
                                                text(issue, "code"),
                                                text(issue, "message")))
                        .toList();
        return new ImportJobOut(
                jobId,
                ImportStatus.valueOf(text(row, "status")),
                json.list(row.get("file_manifest")),
                json.map(row.get("summary")),
                instant(row.get("created_at")),
                instant(row.get("completed_at")),
                issues);
    }

    private void importProducts(String jobId, ParsedFile file, Map<String, Integer> counts) {
        var sku = header(file.headers(), "Internal ID", true);
        var brand = header(file.headers(), "Brand SKU", true);
        var name = header(file.headers(), "Name (CN/EN)", true);
        var market = header(file.headers(), "Market", true);
        var rowNumber = 1;
        for (var row : file.rows()) {
            rowNumber++;
            var skuValue = text(row.get(sku));
            if (skuValue.isBlank()) {
                issue(
                        jobId,
                        "error",
                        file.name(),
                        rowNumber,
                        sku,
                        "MISSING_SKU",
                        "Product SKU is required");
                continue;
            }
            var products = jdbc.queryForList("select id from product where sku = ?", skuValue);
            var productId =
                    products.isEmpty()
                            ? UUID.randomUUID().toString()
                            : text(products.getFirst().get("id"));
            if (products.isEmpty()) {
                jdbc.update(
                        """
                        insert into product
                          (id, sku, brand_sku, name, target_market, created_at)
                        values (?, ?, ?, ?, ?, ?)
                        """,
                        productId,
                        skuValue,
                        text(row.get(brand)),
                        text(row.get(name)),
                        text(row.get(market)),
                        java.sql.Timestamp.from(Instant.now()));
                increment(counts, "products");
            }
            var hash = canonicalJson.sha256(row);
            if (jdbc.queryForList(
                            """
                            select id from product_version
                            where product_id = ? and content_hash = ?
                            """,
                            productId,
                            hash)
                    .isEmpty()) {
                jdbc.update(
                        """
                        insert into product_version
                          (id, product_id, version, source_import_id, payload,
                           content_hash, created_at)
                        values (?, ?, ?, ?, ?::json, ?, ?)
                        """,
                        UUID.randomUUID().toString(),
                        productId,
                        nextVersion("product_version", "product_id", productId),
                        jobId,
                        json.write(row),
                        hash,
                        java.sql.Timestamp.from(Instant.now()));
                increment(counts, "product_versions");
            }
        }
    }

    private void importFactors(String jobId, ParsedFile file, Map<String, Integer> counts) {
        var materialColumn = header(file.headers(), "Material Code", false);
        var nameColumn = firstHeader(file.headers(), "Name (CN/EN)", "Energy Type", "Type (CN/EN)");
        var unit = header(file.headers(), "Unit", true);
        var factorValue = header(file.headers(), "Factor Value", true);
        var co2e = header(file.headers(), "CO2e Unit", true);
        var source = header(file.headers(), "Source", true);
        var standard = header(file.headers(), "Standard", false);
        var category = header(file.headers(), "Category", false);
        var quality = header(file.headers(), "Data Quality", false);
        var region = header(file.headers(), "Region", false);
        var year = header(file.headers(), "Year", false);
        var rowNumber = 1;
        for (var row : file.rows()) {
            rowNumber++;
            var materialCode = materialColumn == null ? "" : text(row.get(materialColumn));
            var factorName =
                    nameColumn == null ? "Factor row " + rowNumber : text(row.get(nameColumn));
            var factorCode =
                    materialCode.isBlank()
                            ? "CF-" + canonicalJson.sha256(factorName).substring(0, 12)
                            : factorCode(materialCode);
            if (!materialCode.isBlank()
                    && jdbc.queryForList("select id from material where code = ?", materialCode)
                            .isEmpty()) {
                jdbc.update(
                        """
                        insert into material
                          (id, code, name, category, created_at)
                        values (?, ?, ?, ?, ?)
                        """,
                        UUID.randomUUID().toString(),
                        materialCode,
                        factorName,
                        category == null ? null : text(row.get(category)),
                        java.sql.Timestamp.from(Instant.now()));
                increment(counts, "materials");
            }
            var factors =
                    jdbc.queryForList(
                            "select id from emission_factor where factor_code = ?", factorCode);
            var factorId =
                    factors.isEmpty()
                            ? UUID.randomUUID().toString()
                            : text(factors.getFirst().get("id"));
            if (factors.isEmpty()) {
                jdbc.update(
                        """
                        insert into emission_factor
                          (id, factor_code, material_code, name, created_at)
                        values (?, ?, ?, ?, ?)
                        """,
                        factorId,
                        factorCode,
                        blankToNull(materialCode),
                        factorName,
                        java.sql.Timestamp.from(Instant.now()));
            }
            var payload = new LinkedHashMap<String, Object>();
            payload.put("value", text(row.get(factorValue)));
            payload.put("activity_unit", text(row.get(unit)));
            payload.put("co2e_unit", text(row.get(co2e)));
            payload.put("source", text(row.get(source)));
            payload.put("standard", optional(row, standard));
            payload.put("region", optional(row, region));
            payload.put("year", optional(row, year));
            payload.put("quality", optional(row, quality));
            var hash = canonicalJson.sha256(payload);
            if (jdbc.queryForList(
                            """
                            select id from factor_version
                            where factor_id = ? and content_hash = ?
                            """,
                            factorId,
                            hash)
                    .isEmpty()) {
                var value = decimal(row.get(factorValue));
                jdbc.update(
                        """
                        insert into factor_version
                          (id, factor_id, version, value, activity_unit, co2e_unit,
                           source, standard, region, reference_year, data_quality,
                           content_hash, approved, created_at)
                        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, false, ?)
                        """,
                        UUID.randomUUID().toString(),
                        factorId,
                        nextVersion("factor_version", "factor_id", factorId),
                        value,
                        text(row.get(unit)),
                        text(row.get(co2e)),
                        text(row.get(source)),
                        optional(row, standard),
                        optional(row, region),
                        optionalInteger(row, year),
                        optional(row, quality),
                        hash,
                        java.sql.Timestamp.from(Instant.now()));
                increment(counts, "factor_versions");
                if (value.signum() < 0) {
                    issue(
                            jobId,
                            "warning",
                            file.name(),
                            rowNumber,
                            factorValue,
                            "NEGATIVE_FACTOR_REVIEW",
                            factorCode + " has a negative factor and requires LCA method review");
                }
            }
        }
    }

    private void importBom(String jobId, ParsedFile file, Map<String, Integer> counts) {
        var sku = header(file.headers(), "Internal ID", true);
        var part = header(file.headers(), "Part Name", true);
        var type = header(file.headers(), "Type", true);
        var materialColumn = header(file.headers(), "Material Code", true);
        var quantity = header(file.headers(), "Qty", true);
        var unit = header(file.headers(), "Unit", true);
        var weight = header(file.headers(), "Weight", true);
        var cf = header(file.headers(), "CF ID", true);
        var lineCounters = new HashMap<String, Integer>();
        var rowNumber = 1;
        for (var row : file.rows()) {
            rowNumber++;
            var versions =
                    jdbc.queryForList(
                            """
                            select v.id from product_version v
                            join product p on p.id = v.product_id
                            where p.sku = ? order by v.version desc limit 1
                            """,
                            text(row.get(sku)));
            if (versions.isEmpty()) {
                issue(
                        jobId,
                        "error",
                        file.name(),
                        rowNumber,
                        null,
                        "UNKNOWN_PRODUCT",
                        "Unknown product: " + text(row.get(sku)));
                continue;
            }
            var productVersionId = text(versions.getFirst().get("id"));
            var lineNo = lineCounters.merge(productVersionId, 1, Integer::sum);
            var materialCode = text(row.get(materialColumn));
            var materials =
                    jdbc.queryForList("select id from material where code = ?", materialCode);
            if (materials.isEmpty()) {
                issue(
                        jobId,
                        "error",
                        file.name(),
                        rowNumber,
                        materialColumn,
                        "UNKNOWN_MATERIAL",
                        "Material not found in factor master: " + materialCode);
                continue;
            }
            var requestedFactor = text(row.get(cf));
            if (requestedFactor.isBlank()) requestedFactor = factorCode(materialCode);
            var versionsForFactor =
                    jdbc.queryForList(
                            """
                            select v.id from factor_version v
                            join emission_factor f on f.id = v.factor_id
                            where f.factor_code = ? and f.material_code = ?
                            order by v.version desc limit 1
                            """,
                            requestedFactor,
                            materialCode);
            var factorId =
                    versionsForFactor.isEmpty() ? null : versionsForFactor.getFirst().get("id");
            if (factorId == null) {
                issue(
                        jobId,
                        "error",
                        file.name(),
                        rowNumber,
                        cf,
                        "FACTOR_MAPPING_MISSING",
                        "No factor version for " + materialCode + "/" + requestedFactor);
            }
            var materialType = text(row.get(type));
            var stage =
                    materialType.contains("Packaging") || materialType.contains("鍖呮潗")
                            ? "packaging"
                            : "raw_materials";
            jdbc.update(
                    """
                    insert into bom_line
                      (id, product_version_id, line_no, material_id, part_name,
                       material_type, quantity, unit, weight_kg_each, factor_version_id,
                       stage, source_row, created_at)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    on conflict (product_version_id, line_no) do nothing
                    """,
                    UUID.randomUUID().toString(),
                    productVersionId,
                    lineNo,
                    materials.getFirst().get("id"),
                    text(row.get(part)),
                    materialType,
                    decimal(row.get(quantity)),
                    text(row.get(unit)),
                    decimal(row.get(weight)),
                    factorId,
                    stage,
                    rowNumber,
                    java.sql.Timestamp.from(Instant.now()));
            increment(counts, "bom_lines");
        }
    }

    private void importRoute(String jobId, ParsedFile file, Map<String, Integer> counts) {
        var products = jdbc.queryForList("select id from product where sku = 'INT-WD-001'");
        if (products.isEmpty()) {
            issue(
                    jobId,
                    "error",
                    file.name(),
                    null,
                    null,
                    "PILOT_PRODUCT_MISSING",
                    "INT-WD-001 not imported");
            return;
        }
        var productId = products.getFirst().get("id");
        if (!jdbc.queryForList(
                        """
                                select id from process_route
                                where product_id = ? and version = 'WD-ROUTE-V1'
                                """,
                        productId)
                .isEmpty()) return;
        var routeId = UUID.randomUUID().toString();
        jdbc.update(
                """
                insert into process_route
                  (id, product_id, route_code, version, approved, created_at)
                values (?, ?, 'WARDROBE-GATE', 'WD-ROUTE-V1', false, ?)
                """,
                routeId,
                productId,
                java.sql.Timestamp.from(Instant.now()));
        var process = header(file.headers(), "Process ID", true);
        var name = header(file.headers(), "Name (CN/EN)", true);
        var time = header(file.headers(), "Std Time", true);
        var energy = header(file.headers(), "Energy Factor", true);
        var sequence = 0;
        for (var index = file.rows().size() - 1; index >= 0; index--) {
            var row = file.rows().get(index);
            jdbc.update(
                    """
                    insert into route_step
                      (id, route_id, sequence, process_code, name,
                       standard_time_min, energy_kwh_per_unit, created_at)
                    values (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    UUID.randomUUID().toString(),
                    routeId,
                    ++sequence,
                    text(row.get(process)),
                    text(row.get(name)),
                    decimal(row.get(time)),
                    decimal(row.get(energy)),
                    java.sql.Timestamp.from(Instant.now()));
            increment(counts, "route_steps");
        }
        increment(counts, "routes");
    }

    private void importEquipment(ParsedFile file, Map<String, Integer> counts) {
        var code = header(file.headers(), "Equip ID", true);
        var process = header(file.headers(), "Process ID", true);
        var name = header(file.headers(), "Name (CN/EN)", true);
        var area = header(file.headers(), "Area", true);
        var power = header(file.headers(), "Power", true);
        var energy = header(file.headers(), "Energy Type", true);
        for (var row : file.rows()) {
            var equipmentCode = text(row.get(code));
            if (!jdbc.queryForList(
                            "select id from equipment where equipment_code = ?", equipmentCode)
                    .isEmpty()) continue;
            var processCode = text(row.get(process));
            var pool =
                    startsWithAny(processCode, "AUX-", "ENV-", "UTIL-", "GREEN-")
                            ? processCode.split("-")[0]
                            : null;
            jdbc.update(
                    """
                    insert into equipment
                      (id, equipment_code, name, process_code, area, rated_power_kw,
                       energy_type, allocation_pool, created_at)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    UUID.randomUUID().toString(),
                    equipmentCode,
                    text(row.get(name)),
                    pool == null ? processCode : null,
                    text(row.get(area)),
                    decimal(row.get(power)),
                    text(row.get(energy)),
                    pool,
                    java.sql.Timestamp.from(Instant.now()));
            increment(counts, "equipment");
        }
    }

    private void importSuppliers(ParsedFile file, Map<String, Integer> counts) {
        var code = header(file.headers(), "Supplier ID", true);
        var name = header(file.headers(), "Name (CN/EN)", true);
        var category = header(file.headers(), "Category", true);
        var certs = header(file.headers(), "Certs", true);
        for (var row : file.rows()) {
            var supplierCode = text(row.get(code));
            if (supplierCode.isBlank()
                    || !jdbc.queryForList(
                                    "select id from supplier where supplier_code = ?", supplierCode)
                            .isEmpty()) continue;
            jdbc.update(
                    """
                    insert into supplier
                      (id, supplier_code, name, category, certifications,
                       is_test, created_at)
                    values (?, ?, ?, ?, ?, ?, ?)
                    """,
                    UUID.randomUUID().toString(),
                    supplierCode,
                    text(row.get(name)),
                    text(row.get(category)),
                    text(row.get(certs)),
                    supplierCode.toUpperCase().startsWith("TEST"),
                    java.sql.Timestamp.from(Instant.now()));
            increment(counts, "suppliers");
        }
    }

    private void scanTestRecords(String jobId, ParsedFile file) {
        var dataId = header(file.headers(), "Data_ID", true);
        var rowNumber = 1;
        for (var row : file.rows()) {
            rowNumber++;
            var id = text(row.get(dataId));
            if (id.toUpperCase().startsWith("TEST")) {
                issue(
                        jobId,
                        "warning",
                        file.name(),
                        rowNumber,
                        dataId,
                        "TEST_RECORD_ISOLATED",
                        "Test record " + id + " was not imported");
            }
        }
    }

    private void persistFailure(
            String jobId, String actor, List<Map<String, Object>> manifest, String error) {
        jdbc.update(
                """
                insert into import_job
                  (id, status, created_by, file_manifest, summary,
                   completed_at, created_at)
                values (?, 'failed', ?, ?::json, ?::json, ?, ?)
                on conflict (id) do update set status = 'failed',
                  summary = excluded.summary, completed_at = excluded.completed_at
                """,
                jobId,
                actor,
                json.write(manifest),
                json.write(Map.of("error", error)),
                java.sql.Timestamp.from(Instant.now()),
                java.sql.Timestamp.from(Instant.now()));
        audit.record(
                actor, "import.failed", "import_job", jobId, null, null, Map.of("error", error));
    }

    private void issue(
            String jobId,
            String severity,
            String fileName,
            Integer rowNumber,
            String field,
            String code,
            String message) {
        jdbc.update(
                """
                insert into import_issue
                  (id, import_job_id, severity, file_name, row_number, field,
                   code, message, created_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                UUID.randomUUID().toString(),
                jobId,
                severity,
                fileName,
                rowNumber,
                field,
                code,
                message,
                java.sql.Timestamp.from(Instant.now()));
    }

    private int nextVersion(String table, String parentColumn, String parentId) {
        if (!List.of("product_version", "factor_version").contains(table)
                || !List.of("product_id", "factor_id").contains(parentColumn)) {
            throw new IllegalArgumentException("Unsupported version target");
        }
        var value =
                jdbc.queryForObject(
                        "select coalesce(max(version), 0) + 1 from "
                                + table
                                + " where "
                                + parentColumn
                                + " = ?",
                        Integer.class,
                        parentId);
        return value == null ? 1 : value;
    }

    private static String header(List<String> headers, String needle, boolean required) {
        var exact = headers.stream().filter(value -> value.equals(needle)).findFirst();
        var found =
                exact.orElseGet(
                        () ->
                                headers.stream()
                                        .filter(
                                                value ->
                                                        value.toLowerCase()
                                                                .contains(needle.toLowerCase()))
                                        .findFirst()
                                        .orElse(null));
        if (required && found == null) {
            throw new IllegalArgumentException("Required column not found: " + needle);
        }
        return found;
    }

    private static String firstHeader(List<String> headers, String... needles) {
        for (var needle : needles) {
            var found = header(headers, needle, false);
            if (found != null) return found;
        }
        return null;
    }

    private static Object optional(Map<String, Object> row, String column) {
        return column == null ? null : blankToNull(text(row.get(column)));
    }

    private static Integer optionalInteger(Map<String, Object> row, String column) {
        if (column == null || row.get(column) == null) return null;
        return decimal(row.get(column)).intValue();
    }

    private static BigDecimal decimal(Object value) {
        if (value == null || String.valueOf(value).isBlank()) return BigDecimal.ZERO;
        return new BigDecimal(String.valueOf(value));
    }

    private static String factorCode(String materialCode) {
        return materialCode.startsWith("RM")
                ? "CF" + materialCode.substring(2)
                : "CF-" + materialCode;
    }

    private static void increment(Map<String, Integer> counts, String key) {
        counts.merge(key, 1, Integer::sum);
    }

    private static String text(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private static String text(Map<String, Object> row, String key) {
        var value = row.get(key);
        return value == null ? null : String.valueOf(value);
    }

    private static Object blankToNull(String value) {
        return value == null || value.isBlank() ? null : value;
    }

    private static boolean startsWithAny(String value, String... prefixes) {
        for (var prefix : prefixes) {
            if (value.startsWith(prefix)) return true;
        }
        return false;
    }

    private static Integer integer(Object value) {
        return value == null ? null : ((Number) value).intValue();
    }

    private static Instant instant(Object value) {
        if (value == null) return null;
        if (value instanceof Instant result) return result;
        if (value instanceof java.sql.Timestamp timestamp) return timestamp.toInstant();
        return Instant.parse(String.valueOf(value));
    }

    private static String rootMessage(Throwable throwable) {
        var current = throwable;
        while (current.getCause() != null) current = current.getCause();
        return current.getMessage() == null
                ? current.getClass().getSimpleName()
                : current.getMessage();
    }
}
