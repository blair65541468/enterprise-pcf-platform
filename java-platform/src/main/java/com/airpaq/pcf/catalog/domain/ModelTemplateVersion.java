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
@Table(name = "model_template_version")
public class ModelTemplateVersion {
    @Id private String id;

    @Column(name = "template_id")
    private String templateId;

    private String version;

    @Column(name = "product_system_uuid")
    private String productSystemUuid;

    @Column(name = "impact_method_uuid")
    private String impactMethodUuid;

    @Column(name = "database_version")
    private String databaseVersion;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "parameter_schema", columnDefinition = "json")
    private Map<String, Object> parameterSchema;

    private boolean approved;

    @Column(name = "created_at")
    private Instant createdAt;

    protected ModelTemplateVersion() {}
}
