package com.airpaq.pcf.calculations.domain;

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
