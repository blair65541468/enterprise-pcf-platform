package com.airpaq.pcf.catalog.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(name = "transport_activity")
public class TransportActivity {
    @Id private String id;

    @Column(name = "product_version_id")
    private String productVersionId;

    @Column(name = "material_id")
    private String materialId;

    @Column(name = "supplier_id")
    private String supplierId;

    private String mode;

    @Column(name = "distance_km")
    private BigDecimal distanceKm;

    @Column(name = "mass_kg")
    private BigDecimal massKg;

    @Column(name = "load_factor")
    private BigDecimal loadFactor;

    @Column(name = "factor_version_id")
    private String factorVersionId;

    private String source;
    private boolean approved;

    @Column(name = "created_at")
    private Instant createdAt;

    protected TransportActivity() {}
}
