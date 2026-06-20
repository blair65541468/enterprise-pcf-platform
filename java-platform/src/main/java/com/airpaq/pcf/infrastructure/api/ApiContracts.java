package com.airpaq.pcf.infrastructure.api;

import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;

public final class ApiContracts {

    private ApiContracts() {}

    @Schema(enumAsRef = true)
    public enum ImportStatus {
        uploaded,
        processing,
        validated,
        failed
    }

    @Schema(enumAsRef = true)
    public enum CalculationStatus {
        draft,
        validated,
        queued,
        calculating,
        calculated,
        submitted,
        approved,
        rejected,
        superseded,
        failed
    }

    public record ImportIssueOut(
            String severity,
            String fileName,
            Integer rowNumber,
            String field,
            String code,
            String message) {}

    public record ImportJobOut(
            String id,
            ImportStatus status,
            List<Map<String, Object>> fileManifest,
            Map<String, Object> summary,
            Instant createdAt,
            Instant completedAt,
            List<ImportIssueOut> issues) {}

    public record SnapshotCreate(String factorSetVersion, String routeVersion, String boundary) {
        public SnapshotCreate {
            factorSetVersion = factorSetVersion == null ? "2026.06" : factorSetVersion;
            routeVersion = routeVersion == null ? "WD-ROUTE-V1" : routeVersion;
            boundary = boundary == null ? "cradle_to_gate_with_packaging" : boundary;
        }
    }

    public record SnapshotOut(
            String id,
            int version,
            String factorSetVersion,
            String boundary,
            String manifestHash,
            List<Map<String, Object>> validationErrors,
            Instant createdAt) {}

    public record CalculationCreate(
            String sku,
            @NotNull Integer snapshotVersion,
            String modelTemplateVersion,
            String factorSetVersion,
            String routeVersion,
            String impactMethod,
            String boundary,
            @NotBlank @Size(min = 5, max = 200) String idempotencyKey) {
        public CalculationCreate {
            sku = sku == null ? "INT-WD-001" : sku;
            modelTemplateVersion =
                    modelTemplateVersion == null ? "WARDROBE-GATE-V1" : modelTemplateVersion;
            factorSetVersion = factorSetVersion == null ? "2026.06" : factorSetVersion;
            routeVersion = routeVersion == null ? "WD-ROUTE-V1" : routeVersion;
            impactMethod = impactMethod == null ? "IPCC-2021-ISO14067-GWP100" : impactMethod;
            boundary = boundary == null ? "cradle_to_gate_with_packaging" : boundary;
        }
    }

    @JsonInclude(JsonInclude.Include.ALWAYS)
    public record ResultSummaryOut(
            BigDecimal totalKgCo2e,
            String functionalUnit,
            String boundary,
            String impactMethod,
            BigDecimal aircraft,
            BigDecimal biogenicEmissions,
            BigDecimal biogenicRemovals,
            BigDecimal fossil,
            BigDecimal landUseChange,
            BigDecimal rawMaterials,
            BigDecimal inboundTransport,
            BigDecimal manufacturing,
            BigDecimal packaging,
            String dataQualityStatus) {}

    public record CalculationOut(
            String id,
            CalculationStatus status,
            String idempotencyKey,
            String impactMethod,
            String engine,
            String error,
            String manifestHash,
            Instant createdAt,
            ResultSummaryOut summary) {}

    public record ContributionOut(
            String dimension,
            String code,
            String name,
            BigDecimal amountKgCo2e,
            Integer rank,
            Map<String, Object> metadataJson) {}

    public record RejectionRequest(@NotBlank @Size(min = 5, max = 2000) String reason) {}

    public record FactorApproval(
            @DecimalMin(value = "0", inclusive = false) BigDecimal densityKgM3,
            String licenceRef) {}

    public record MappingCreate(
            @NotBlank String materialCode,
            @NotBlank String processUuid,
            @NotBlank String referenceFlowUuid,
            @NotBlank String openlcaUnit,
            @NotNull Map<String, Object> conversionRule,
            String region,
            Integer referenceYear,
            @NotBlank String databaseVersion) {}

    public record TransportCreate(
            @NotBlank String mode,
            @NotNull @DecimalMin(value = "0", inclusive = false) BigDecimal distanceKm,
            @NotNull @DecimalMin(value = "0", inclusive = false) BigDecimal massKg,
            @DecimalMin(value = "0", inclusive = false) @DecimalMax("1") BigDecimal loadFactor,
            @NotBlank String factorCode,
            @NotBlank String source) {}

    public record ModelTemplateCreate(
            String code,
            String name,
            String productFamily,
            String version,
            @NotBlank String productSystemUuid,
            @NotBlank String impactMethodUuid,
            @NotBlank String databaseVersion,
            Map<String, Object> parameterSchema) {
        public ModelTemplateCreate {
            code = code == null ? "WARDROBE-GATE" : code;
            name = name == null ? "Board wardrobe cradle-to-gate PCF" : name;
            productFamily = productFamily == null ? "wardrobe" : productFamily;
            version = version == null ? "WARDROBE-GATE-V1" : version;
            parameterSchema = parameterSchema == null ? Map.of() : parameterSchema;
        }
    }
}
