package com.airpaq.pcf.calculations.api.dto;

import io.swagger.v3.oas.annotations.media.Schema;

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
