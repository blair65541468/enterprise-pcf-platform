package com.airpaq.pcf.catalog.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(name = "bom_line")
public class BomLine {
    @Id private String id;

    @Column(name = "product_version_id")
    private String productVersionId;

    @Column(name = "line_no")
    private int lineNo;

    @Column(name = "material_id")
    private String materialId;

    @Column(name = "part_name")
    private String partName;

    @Column(name = "material_type")
    private String materialType;

    private BigDecimal quantity;
    private String unit;

    @Column(name = "weight_kg_each")
    private BigDecimal weightKgEach;

    @Column(name = "factor_version_id")
    private String factorVersionId;

    private String stage;

    @Column(name = "source_row")
    private Integer sourceRow;

    @Column(name = "created_at")
    private Instant createdAt;

    protected BomLine() {}
}
