package com.airpaq.pcf.catalog.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "emission_factor")
public class EmissionFactor {
    @Id private String id;

    @Column(name = "factor_code")
    private String factorCode;

    @Column(name = "material_code")
    private String materialCode;

    private String name;

    @Column(name = "created_at")
    private Instant createdAt;

    protected EmissionFactor() {}
}
