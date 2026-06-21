package com.airpaq.pcf.calculations.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(name = "result_summary")
public class ResultSummary {
    @Id private String id;

    @Column(name = "run_id")
    private String runId;

    @Column(name = "total_kg_co2e")
    private BigDecimal totalKgCo2e;

    @Column(name = "functional_unit")
    private String functionalUnit;

    private String boundary;

    @Column(name = "impact_method")
    private String impactMethod;

    private BigDecimal aircraft;

    @Column(name = "biogenic_emissions")
    private BigDecimal biogenicEmissions;

    @Column(name = "biogenic_removals")
    private BigDecimal biogenicRemovals;

    private BigDecimal fossil;

    @Column(name = "land_use_change")
    private BigDecimal landUseChange;

    @Column(name = "raw_materials")
    private BigDecimal rawMaterials;

    @Column(name = "inbound_transport")
    private BigDecimal inboundTransport;

    private BigDecimal manufacturing;
    private BigDecimal packaging;

    @Column(name = "data_quality_status")
    private String dataQualityStatus;

    @Column(name = "created_at")
    private Instant createdAt;

    protected ResultSummary() {}
}
