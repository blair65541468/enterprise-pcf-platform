package com.airpaq.pcf.calculations.api.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

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
