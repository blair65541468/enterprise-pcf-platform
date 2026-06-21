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
@Table(name = "material_process_mapping")
public class MaterialProcessMapping {
    @Id private String id;

    @Column(name = "material_id")
    private String materialId;

    @Column(name = "process_uuid")
    private String processUuid;

    @Column(name = "reference_flow_uuid")
    private String referenceFlowUuid;

    @Column(name = "openlca_unit")
    private String openLcaUnit;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "conversion_rule", columnDefinition = "json")
    private Map<String, Object> conversionRule;

    private String region;

    @Column(name = "reference_year")
    private Integer referenceYear;

    @Column(name = "database_version")
    private String databaseVersion;

    private String status;

    @Column(name = "reviewed_by")
    private String reviewedBy;

    @Column(name = "created_at")
    private Instant createdAt;

    protected MaterialProcessMapping() {}
}
