package com.airpaq.pcf.catalog.api.dto;

import jakarta.validation.constraints.NotBlank;
import java.util.Map;

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
