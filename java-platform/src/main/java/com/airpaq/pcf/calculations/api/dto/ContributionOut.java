package com.airpaq.pcf.calculations.api.dto;

import java.math.BigDecimal;
import java.util.Map;

public record ContributionOut(
        String dimension,
        String code,
        String name,
        BigDecimal amountKgCo2e,
        Integer rank,
        Map<String, Object> metadataJson) {}
