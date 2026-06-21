package com.airpaq.pcf.calculations.api.dto;

import java.time.Instant;

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
