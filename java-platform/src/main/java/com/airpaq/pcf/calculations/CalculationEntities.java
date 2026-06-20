package com.airpaq.pcf.calculations;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

final class CalculationEntities {
    private CalculationEntities() {}
}

@Entity
@Table(name = "calculation_snapshot")
class CalculationSnapshotEntity {
    @Id String id;

    @Column(name = "product_id")
    String productId;

    int version;

    @Column(name = "product_version_id")
    String productVersionId;

    @Column(name = "route_id")
    String routeId;

    @Column(name = "factor_set_version")
    String factorSetVersion;

    String boundary;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "json")
    Object payload;

    @Column(name = "manifest_hash")
    String manifestHash;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "validation_errors", columnDefinition = "json")
    Object validationErrors;

    @Column(name = "created_by")
    String createdBy;

    @Column(name = "created_at")
    Instant createdAt;
}

@Entity
@Table(name = "calculation_run")
class CalculationRunEntity {
    @Id String id;

    @Column(name = "snapshot_id")
    String snapshotId;

    @Column(name = "product_id")
    String productId;

    @Column(name = "model_template_version_id")
    String modelTemplateVersionId;

    @Column(name = "idempotency_key")
    String idempotencyKey;

    @Column(name = "request_hash")
    String requestHash;

    String status;

    @Column(name = "execution_token")
    String executionToken;

    @Column(name = "attempt_count")
    int attemptCount;

    @Column(name = "heartbeat_at")
    Instant heartbeatAt;

    @Column(name = "impact_method")
    String impactMethod;

    @Column(name = "requested_by")
    String requestedBy;

    @Column(name = "submitted_by")
    String submittedBy;

    @Column(name = "approved_by")
    String approvedBy;

    @Column(name = "rejection_reason")
    String rejectionReason;

    String engine;

    @Column(name = "engine_version")
    String engineVersion;

    @Column(name = "raw_result_object_key")
    String rawResultObjectKey;

    String error;

    @Column(name = "started_at")
    Instant startedAt;

    @Column(name = "completed_at")
    Instant completedAt;

    @Column(name = "submitted_at")
    Instant submittedAt;

    @Column(name = "approved_at")
    Instant approvedAt;

    @Column(name = "manifest_hash")
    String manifestHash;

    @Column(name = "created_at")
    Instant createdAt;
}

@Entity
@Table(name = "result_summary")
class ResultSummaryEntity {
    @Id String id;

    @Column(name = "run_id")
    String runId;

    @Column(name = "total_kg_co2e")
    BigDecimal totalKgCo2e;

    @Column(name = "functional_unit")
    String functionalUnit;

    String boundary;

    @Column(name = "impact_method")
    String impactMethod;

    BigDecimal aircraft;

    @Column(name = "biogenic_emissions")
    BigDecimal biogenicEmissions;

    @Column(name = "biogenic_removals")
    BigDecimal biogenicRemovals;

    BigDecimal fossil;

    @Column(name = "land_use_change")
    BigDecimal landUseChange;

    @Column(name = "raw_materials")
    BigDecimal rawMaterials;

    @Column(name = "inbound_transport")
    BigDecimal inboundTransport;

    BigDecimal manufacturing;
    BigDecimal packaging;

    @Column(name = "data_quality_status")
    String dataQualityStatus;

    @Column(name = "created_at")
    Instant createdAt;
}

@Entity
@Table(name = "result_contribution")
class ResultContributionEntity {
    @Id String id;

    @Column(name = "run_id")
    String runId;

    String dimension;
    String code;
    String name;

    @Column(name = "amount_kg_co2e")
    BigDecimal amountKgCo2e;

    Integer rank;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "metadata_json", columnDefinition = "json")
    Object metadataJson;

    @Column(name = "created_at")
    Instant createdAt;
}

@Entity
@Table(name = "outbox_event")
class OutboxEventEntity {
    @Id String id;

    @Column(name = "event_type")
    String eventType;

    @Column(name = "aggregate_type")
    String aggregateType;

    @Column(name = "aggregate_id")
    String aggregateId;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "json")
    Object payload;

    @Column(name = "published_at")
    Instant publishedAt;

    @Column(name = "attempt_count")
    int attemptCount;

    @Column(name = "last_error")
    String lastError;

    @Column(name = "created_at")
    Instant createdAt;
}
