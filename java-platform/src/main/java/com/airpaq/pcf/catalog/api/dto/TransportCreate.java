package com.airpaq.pcf.catalog.api.dto;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;

public record TransportCreate(
        @NotBlank String mode,
        @NotNull @DecimalMin(value = "0", inclusive = false) BigDecimal distanceKm,
        @NotNull @DecimalMin(value = "0", inclusive = false) BigDecimal massKg,
        @DecimalMin(value = "0", inclusive = false) @DecimalMax("1") BigDecimal loadFactor,
        @NotBlank String factorCode,
        @NotBlank String source) {}
