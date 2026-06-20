package com.airpaq.pcf.calculations.messaging;

import java.time.Instant;

public record CalculationMessage(
        int schemaVersion, String eventId, String runId, String requestId, Instant occurredAt) {}
