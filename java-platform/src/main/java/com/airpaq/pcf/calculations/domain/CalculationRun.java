package com.airpaq.pcf.calculations.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "calculation_run")
public class CalculationRun {
    @Id private String id;

    @Column(name = "snapshot_id")
    private String snapshotId;

    @Column(name = "product_id")
    private String productId;

    @Column(name = "model_template_version_id")
    private String modelTemplateVersionId;

    @Column(name = "idempotency_key")
    private String idempotencyKey;

    @Column(name = "request_hash")
    private String requestHash;

    @Enumerated(EnumType.STRING)
    @Column(columnDefinition = "calculationstatus")
    private CalculationStatus status;

    @Column(name = "execution_token")
    private String executionToken;

    @Column(name = "attempt_count")
    private int attemptCount;

    @Column(name = "heartbeat_at")
    private Instant heartbeatAt;

    @Column(name = "impact_method")
    private String impactMethod;

    @Column(name = "requested_by")
    private String requestedBy;

    @Column(name = "submitted_by")
    private String submittedBy;

    @Column(name = "approved_by")
    private String approvedBy;

    @Column(name = "rejection_reason")
    private String rejectionReason;

    private String engine;

    @Column(name = "engine_version")
    private String engineVersion;

    @Column(name = "raw_result_object_key")
    private String rawResultObjectKey;

    private String error;

    @Column(name = "started_at")
    private Instant startedAt;

    @Column(name = "completed_at")
    private Instant completedAt;

    @Column(name = "submitted_at")
    private Instant submittedAt;

    @Column(name = "approved_at")
    private Instant approvedAt;

    @Column(name = "manifest_hash")
    private String manifestHash;

    @Column(name = "created_at")
    private Instant createdAt;

    protected CalculationRun() {}

    public String id() {
        return id;
    }

    public void submit(String actor) {
        if (status != CalculationStatus.calculated) {
            throw new IllegalStateException("Only calculated runs can be submitted");
        }
        status = CalculationStatus.submitted;
        submittedBy = actor;
    }

    public void approve(String actor) {
        if (status != CalculationStatus.submitted) {
            throw new IllegalStateException("Only submitted runs can be approved");
        }
        if (actor.equals(submittedBy)) {
            throw new IllegalStateException("Four-eyes rule: submitter cannot approve");
        }
        status = CalculationStatus.approved;
        approvedBy = actor;
    }
}
