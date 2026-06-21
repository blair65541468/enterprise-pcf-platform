package com.airpaq.pcf.snapshots.api.dto;

import java.time.Instant;
import java.util.List;
import java.util.Map;

public record SnapshotOut(
        String id,
        int version,
        String factorSetVersion,
        String boundary,
        String manifestHash,
        List<Map<String, Object>> validationErrors,
        Instant createdAt) {}
