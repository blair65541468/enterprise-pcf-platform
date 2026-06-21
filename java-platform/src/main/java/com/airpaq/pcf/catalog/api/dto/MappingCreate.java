package com.airpaq.pcf.catalog.api.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.util.Map;

public record MappingCreate(
        @NotBlank String materialCode,
        @NotBlank String processUuid,
        @NotBlank String referenceFlowUuid,
        @NotBlank String openlcaUnit,
        @NotNull Map<String, Object> conversionRule,
        String region,
        Integer referenceYear,
        @NotBlank String databaseVersion) {}
