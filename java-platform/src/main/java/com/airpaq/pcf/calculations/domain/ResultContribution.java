package com.airpaq.pcf.calculations.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.Map;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "result_contribution")
public class ResultContribution {
    @Id private String id;

    @Column(name = "run_id")
    private String runId;

    private String dimension;
    private String code;
    private String name;

    @Column(name = "amount_kg_co2e")
    private BigDecimal amountKgCo2e;

    private Integer rank;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "metadata_json", columnDefinition = "json")
    private Map<String, Object> metadataJson;

    @Column(name = "created_at")
    private Instant createdAt;

    protected ResultContribution() {}
}
