package com.airpaq.pcf.catalog.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "material")
public class Material {
    @Id private String id;
    private String code;
    private String name;
    private String category;

    @Column(name = "created_at")
    private Instant createdAt;

    protected Material() {}
}
