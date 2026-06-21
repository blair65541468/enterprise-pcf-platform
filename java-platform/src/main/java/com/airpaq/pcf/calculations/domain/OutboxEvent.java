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
@Table(name = "outbox_event")
public class OutboxEvent {
    @Id private String id;

    @Column(name = "event_type")
    private String eventType;

    @Column(name = "aggregate_type")
    private String aggregateType;

    @Column(name = "aggregate_id")
    private String aggregateId;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "json")
    private Map<String, Object> payload;

    @Column(name = "published_at")
    private Instant publishedAt;

    @Column(name = "attempt_count")
    private int attemptCount;

    @Column(name = "last_error")
    private String lastError;

    @Column(name = "created_at")
    private Instant createdAt;

    protected OutboxEvent() {}

    public String id() {
        return id;
    }

    public Map<String, Object> payload() {
        return Map.copyOf(payload);
    }

    public void markPublished(Instant timestamp) {
        publishedAt = timestamp;
        lastError = null;
    }

    public void markFailed(String message) {
        attemptCount++;
        lastError = message;
    }
}
