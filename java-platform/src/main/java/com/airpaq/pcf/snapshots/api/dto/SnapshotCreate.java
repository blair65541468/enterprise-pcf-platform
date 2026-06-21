package com.airpaq.pcf.snapshots.api.dto;

public record SnapshotCreate(String factorSetVersion, String routeVersion, String boundary) {
    public SnapshotCreate {
        factorSetVersion = factorSetVersion == null ? "2026.06" : factorSetVersion;
        routeVersion = routeVersion == null ? "WD-ROUTE-V1" : routeVersion;
        boundary = boundary == null ? "cradle_to_gate_with_packaging" : boundary;
    }
}
