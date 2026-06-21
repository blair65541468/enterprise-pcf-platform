package com.airpaq.pcf.catalog.api.dto;

import jakarta.validation.constraints.DecimalMin;
import java.math.BigDecimal;

public record FactorApproval(
        @DecimalMin(value = "0", inclusive = false) BigDecimal densityKgM3, String licenceRef) {}
