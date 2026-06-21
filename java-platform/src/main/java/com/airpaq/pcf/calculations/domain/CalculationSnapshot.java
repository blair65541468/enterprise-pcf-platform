package com.airpaq.pcf.calculations.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.Map;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "calculation_snapshot")
public class CalculationSnapshot {
    @Id private String id;

    @Column(name = "product_id")
    private String productId;

    private int version;

    @Column(name = "product_version_id")
    private String productVersionId;

    @Column(name = "route_id")
    private String routeId;

    @Column(name = "factor_set_version")
    private String factorSetVersion;

    private String boundary;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "json")
    private Map<String, Object> payload;

    @Column(name = "manifest_hash")
    private String manifestHash;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "validation_errors", columnDefinition = "json")
    private Object validationErrors;

    @Column(name = "created_by")
    private String createdBy;

    @Column(name = "created_at")
    private Instant createdAt;

    protected CalculationSnapshot() {}
}
