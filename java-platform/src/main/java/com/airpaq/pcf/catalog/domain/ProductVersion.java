package com.airpaq.pcf.catalog.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.Map;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "product_version")
public class ProductVersion {
    @Id private String id;

    @Column(name = "product_id")
    private String productId;

    private int version;

    @Column(name = "source_import_id")
    private String sourceImportId;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "json")
    private Map<String, Object> payload;

    @Column(name = "content_hash")
    private String contentHash;

    @Column(name = "created_at")
    private Instant createdAt;

    protected ProductVersion() {}
}
