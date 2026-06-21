package com.airpaq.pcf.catalog.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "process_route")
public class ProcessRoute {
    @Id private String id;

    @Column(name = "product_id")
    private String productId;

    @Column(name = "route_code")
    private String routeCode;

    private String version;
    private boolean approved;

    @Column(name = "created_at")
    private Instant createdAt;

    protected ProcessRoute() {}
}
