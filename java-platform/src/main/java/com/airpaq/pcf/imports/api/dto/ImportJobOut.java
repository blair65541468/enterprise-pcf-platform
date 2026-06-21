package com.airpaq.pcf.imports.api.dto;

import java.time.Instant;
import java.util.List;
import java.util.Map;

public record ImportJobOut(
        String id,
        ImportStatus status,
        List<Map<String, Object>> fileManifest,
        Map<String, Object> summary,
        Instant createdAt,
        Instant completedAt,
        List<ImportIssueOut> issues) {}
