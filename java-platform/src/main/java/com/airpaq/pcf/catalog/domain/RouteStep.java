package com.airpaq.pcf.catalog.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(name = "route_step")
public class RouteStep {
    @Id private String id;

    @Column(name = "route_id")
    private String routeId;

    private int sequence;

    @Column(name = "process_code")
    private String processCode;

    private String name;

    @Column(name = "standard_time_min")
    private BigDecimal standardTimeMin;

    @Column(name = "energy_kwh_per_unit")
    private BigDecimal energyKwhPerUnit;

    @Column(name = "created_at")
    private Instant createdAt;

    protected RouteStep() {}
}
