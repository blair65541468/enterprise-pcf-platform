package com.airpaq.pcf.calculations.api.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import java.math.BigDecimal;

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
