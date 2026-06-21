package com.airpaq.pcf.catalog.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(name = "factor_version")
public class FactorVersion {
    @Id private String id;

    @Column(name = "factor_id")
    private String factorId;

    private int version;
    private BigDecimal value;

    @Column(name = "activity_unit")
    private String activityUnit;

    @Column(name = "co2e_unit")
    private String co2eUnit;

    private String source;
    private String standard;
    private String region;

    @Column(name = "reference_year")
    private Integer referenceYear;

    @Column(name = "data_quality")
    private String dataQuality;

    @Column(name = "density_kg_m3")
    private BigDecimal densityKgM3;

    @Column(name = "licence_ref")
    private String licenceRef;

    @Column(name = "content_hash")
    private String contentHash;

    private boolean approved;

    @Column(name = "created_at")
    private Instant createdAt;

    protected FactorVersion() {}

    public void approve(BigDecimal density, String licence, String hash) {
        if (approved) throw new IllegalStateException("Approved factor versions are immutable");
        densityKgM3 = density;
        licenceRef = licence;
        contentHash = hash;
        approved = true;
    }
}
