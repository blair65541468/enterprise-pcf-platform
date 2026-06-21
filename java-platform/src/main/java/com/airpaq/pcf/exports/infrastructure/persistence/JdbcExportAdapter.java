package com.airpaq.pcf.exports.infrastructure.persistence;

import com.airpaq.pcf.exports.application.ExportOperations;
import com.airpaq.pcf.shared.json.CanonicalJson;
import com.airpaq.pcf.shared.json.JsonSupport;
import com.airpaq.pcf.shared.web.DomainException;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.apache.poi.ss.usermodel.FillPatternType;
import org.apache.poi.ss.usermodel.IndexedColors;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

@Service
public class JdbcExportAdapter implements ExportOperations {

    private final JdbcTemplate jdbc;
    private final JsonSupport json;
    private final CanonicalJson canonicalJson;

    public JdbcExportAdapter(JdbcTemplate jdbc, JsonSupport json, CanonicalJson canonicalJson) {
        this.jdbc = jdbc;
        this.json = json;
        this.canonicalJson = canonicalJson;
    }

    public ResponseEntity<byte[]> json(String runId) {
        return response(
                canonicalJson.bytes(exportData(runId)),
                MediaType.APPLICATION_JSON,
                "pcf-" + runId + ".json");
    }

    public ResponseEntity<byte[]> excel(String runId) {
        var bundle = load(runId);
        var run = bundle.run();
        var summary = bundle.summary();
        var snapshot = bundle.snapshot();
        try (var workbook = new XSSFWorkbook();
                var output = new ByteArrayOutputStream()) {
            keyValueSheet(
                    workbook,
                    "鎽樿",
                    List.of(
                            row("Calculation ID", run.get("id")),
                            row("Status", run.get("status")),
                            row("Manifest SHA-256", run.get("manifest_hash")),
                            row("Snapshot SHA-256", run.get("snapshot_manifest_hash")),
                            row("Functional unit", summary.get("functional_unit")),
                            row("Boundary", summary.get("boundary")),
                            row("Impact method", summary.get("impact_method")),
                            row("Total kg CO2e", summary.get("total_kg_co2e")),
                            row("Data quality", summary.get("data_quality_status")),
                            row("Submitted by", run.get("submitted_by")),
                            row("Approved by", run.get("approved_by"))));
            tableSheet(
                    workbook,
                    "闃舵璐＄尞",
                    List.of("闃舵", "kg CO2e"),
                    List.of(
                            row("raw_materials", summary.get("raw_materials")),
                            row("inbound_transport", summary.get("inbound_transport")),
                            row("manufacturing", summary.get("manufacturing")),
                            row("packaging", summary.get("packaging"))));
            tableSheet(
                    workbook,
                    "ISO14067鍒嗙被",
                    List.of("绫诲埆", "kg CO2e"),
                    List.of(
                            row("aircraft", summary.get("aircraft")),
                            row("biogenic_emissions", summary.get("biogenic_emissions")),
                            row("biogenic_removals", summary.get("biogenic_removals")),
                            row("fossil", summary.get("fossil")),
                            row("land_use_change", summary.get("land_use_change")),
                            row("total", summary.get("total_kg_co2e"))));
            mapTable(
                    workbook,
                    "贡献明细",
                    List.of("rank", "dimension", "code", "name", "amount_kg_co2e", "metadata_json"),
                    bundle.contributions());
            mapTable(
                    workbook,
                    "BOM与因子",
                    List.of(
                            "line_no",
                            "material_code",
                            "part_name",
                            "stage",
                            "mass_kg",
                            "activity_amount",
                            "factor_activity_unit",
                            "factor_value",
                            "factor_source",
                            "mapping"),
                    jsonList(snapshot.get("bom")));
            mapTable(
                    workbook,
                    "制造能耗",
                    List.of(
                            "process_code",
                            "name",
                            "amount",
                            "unit",
                            "factor_code",
                            "factor_value",
                            "source"),
                    jsonList(snapshot.get("energy")));
            mapTable(
                    workbook,
                    "入厂运输",
                    List.of(
                            "material_code",
                            "mode",
                            "distance_km",
                            "mass_kg",
                            "load_factor",
                            "factor_code",
                            "factor_value",
                            "source"),
                    jsonList(snapshot.get("transport")));
            var exceptions =
                    run.get("error") == null
                            ? List.of(row("snapshot", "NONE", "无阻断异常"))
                            : List.of(row("calculation", "CALCULATION_ERROR", run.get("error")));
            tableSheet(workbook, "异常项", List.of("来源", "代码", "说明"), exceptions);
            keyValueSheet(
                    workbook,
                    "计算清单",
                    List.of(
                            row("Calculation ID", run.get("id")),
                            row("Calculation manifest SHA-256", run.get("manifest_hash")),
                            row("Snapshot manifest SHA-256", run.get("snapshot_manifest_hash")),
                            row("Snapshot version", run.get("snapshot_version")),
                            row("Factor set version", run.get("factor_set_version")),
                            row("Route version", snapshot.get("route_version")),
                            row("Model template version ID", run.get("model_template_version_id")),
                            row("Impact method", run.get("impact_method")),
                            row("Engine", run.get("engine")),
                            row("Engine version", run.get("engine_version")),
                            row("Raw result object key", run.get("raw_result_object_key")),
                            row("Requested by", run.get("requested_by")),
                            row("Submitted by", run.get("submitted_by")),
                            row("Approved by", run.get("approved_by"))));
            mapTable(
                    workbook,
                    "审批与审计",
                    List.of("occurred_at", "actor", "action", "details"),
                    bundle.audits());
            for (var sheet : workbook) {
                sheet.createFreezePane(0, 1);
                if (sheet.getLastRowNum() >= 0) {
                    sheet.setAutoFilter(
                            new org.apache.poi.ss.util.CellRangeAddress(
                                    0,
                                    Math.max(0, sheet.getLastRowNum()),
                                    0,
                                    Math.max(0, sheet.getRow(0).getLastCellNum() - 1)));
                }
            }
            workbook.write(output);
            return response(
                    output.toByteArray(),
                    MediaType.parseMediaType(
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                    "pcf-" + runId + ".xlsx");
        } catch (IOException exception) {
            throw new IllegalStateException("Unable to create Excel export", exception);
        }
    }

    private Map<String, Object> exportData(String runId) {
        var bundle = load(runId);
        var result = new LinkedHashMap<String, Object>();
        result.put("calculation_id", runId);
        result.put("status", bundle.run().get("status"));
        result.put("manifest_hash", bundle.run().get("manifest_hash"));
        result.put("snapshot_manifest_hash", bundle.run().get("snapshot_manifest_hash"));
        result.put("summary", cleanSummary(bundle.summary()));
        result.put(
                "contributions",
                bundle.contributions().stream()
                        .map(
                                item -> {
                                    var value = new LinkedHashMap<String, Object>();
                                    value.put("dimension", item.get("dimension"));
                                    value.put("code", item.get("code"));
                                    value.put("name", item.get("name"));
                                    value.put("amount_kg_co2e", item.get("amount_kg_co2e"));
                                    value.put("rank", item.get("rank"));
                                    value.put("metadata", json.map(item.get("metadata_json")));
                                    return value;
                                })
                        .toList());
        result.put(
                "audit_events",
                bundle.audits().stream()
                        .map(
                                item -> {
                                    var value = new LinkedHashMap<String, Object>();
                                    value.put("occurred_at", item.get("occurred_at"));
                                    value.put("actor", item.get("actor"));
                                    value.put("action", item.get("action"));
                                    value.put("details", json.map(item.get("details")));
                                    return value;
                                })
                        .toList());
        return result;
    }

    private ExportBundle load(String runId) {
        var runs =
                jdbc.queryForList(
                        """
                        select r.*, s.payload, s.manifest_hash snapshot_manifest_hash,
                          s.version snapshot_version, s.factor_set_version
                        from calculation_run r
                        join calculation_snapshot s on s.id = r.snapshot_id
                        where r.id = ?
                        """,
                        runId);
        if (runs.isEmpty()) throw new DomainException(404, "Calculation not found");
        var run = runs.getFirst();
        if (!"approved".equals(String.valueOf(run.get("status")))) {
            throw new DomainException(403, "Only approved results can be formally exported");
        }
        var summaries = jdbc.queryForList("select * from result_summary where run_id = ?", runId);
        if (summaries.isEmpty()) {
            throw new DomainException(404, "Result summary not found");
        }
        var contributions =
                jdbc.queryForList(
                        """
                        select dimension, code, name, amount_kg_co2e, rank,
                          metadata_json from result_contribution
                        where run_id = ? order by rank nulls last
                        """,
                        runId);
        var audits =
                jdbc.queryForList(
                        """
                        select occurred_at, actor, action, details
                        from audit_event where object_id = ? order by occurred_at
                        """,
                        runId);
        return new ExportBundle(
                run, summaries.getFirst(), json.map(run.get("payload")), contributions, audits);
    }

    private static Map<String, Object> cleanSummary(Map<String, Object> source) {
        var value = new LinkedHashMap<>(source);
        value.remove("id");
        value.remove("run_id");
        value.remove("created_at");
        return value;
    }

    private static ResponseEntity<byte[]> response(byte[] data, MediaType type, String filename) {
        return ResponseEntity.ok()
                .contentType(type)
                .header(
                        HttpHeaders.CONTENT_DISPOSITION,
                        "attachment; filename=\"" + filename + "\"")
                .body(data);
    }

    private static void keyValueSheet(XSSFWorkbook workbook, String name, List<List<Object>> rows) {
        tableSheet(workbook, name, List.of("字段", "值"), rows);
    }

    private static void mapTable(
            XSSFWorkbook workbook,
            String name,
            List<String> headers,
            List<Map<String, Object>> rows) {
        tableSheet(
                workbook,
                name,
                headers,
                rows.stream()
                        .map(
                                item ->
                                        headers.stream()
                                                .map(item::get)
                                                .map(value -> (Object) value)
                                                .toList())
                        .toList());
    }

    private static void tableSheet(
            XSSFWorkbook workbook, String name, List<String> headers, List<List<Object>> rows) {
        var sheet = workbook.createSheet(name);
        var header = sheet.createRow(0);
        var style = workbook.createCellStyle();
        style.setFillForegroundColor(IndexedColors.DARK_BLUE.getIndex());
        style.setFillPattern(FillPatternType.SOLID_FOREGROUND);
        var font = workbook.createFont();
        font.setBold(true);
        font.setColor(IndexedColors.WHITE.getIndex());
        style.setFont(font);
        for (var index = 0; index < headers.size(); index++) {
            var cell = header.createCell(index);
            cell.setCellValue(headers.get(index));
            cell.setCellStyle(style);
        }
        var rowIndex = 1;
        for (var values : rows) {
            var row = sheet.createRow(rowIndex++);
            for (var column = 0; column < values.size(); column++) {
                row.createCell(column).setCellValue(string(values.get(column)));
            }
        }
        for (var index = 0; index < headers.size(); index++) {
            sheet.autoSizeColumn(index);
        }
    }

    private static List<Object> row(Object... values) {
        return List.of(values);
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> jsonList(Object value) {
        return value instanceof List<?> list
                ? list.stream()
                        .filter(Map.class::isInstance)
                        .map(item -> (Map<String, Object>) item)
                        .toList()
                : List.of();
    }

    private static String string(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private record ExportBundle(
            Map<String, Object> run,
            Map<String, Object> summary,
            Map<String, Object> snapshot,
            List<Map<String, Object>> contributions,
            List<Map<String, Object>> audits) {}
}
