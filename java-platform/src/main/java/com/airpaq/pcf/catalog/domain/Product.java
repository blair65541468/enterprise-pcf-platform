package com.airpaq.pcf.catalog.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "product")
public class Product {
    @Id private String id;
    private String sku;

    @Column(name = "brand_sku")
    private String brandSku;

    private String name;

    @Column(name = "target_market")
    private String targetMarket;

    @Column(name = "created_at")
    private Instant createdAt;

    protected Product() {}

    public String id() {
        return id;
    }

    public String sku() {
        return sku;
    }
}
