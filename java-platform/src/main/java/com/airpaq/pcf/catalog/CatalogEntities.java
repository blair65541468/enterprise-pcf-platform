package com.airpaq.pcf.catalog;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

final class CatalogEntities {
    private CatalogEntities() {}
}

@Entity
@Table(name = "product")
class ProductEntity {
    @Id String id;
    String sku;

    @Column(name = "brand_sku")
    String brandSku;

    String name;

    @Column(name = "target_market")
    String targetMarket;

    @Column(name = "created_at")
    Instant createdAt;
}

@Entity
@Table(name = "product_version")
class ProductVersionEntity {
    @Id String id;

    @Column(name = "product_id")
    String productId;

    int version;

    @Column(name = "source_import_id")
    String sourceImportId;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "json")
    Object payload;

    @Column(name = "content_hash")
    String contentHash;

    @Column(name = "created_at")
    Instant createdAt;
}

@Entity
@Table(name = "material")
class MaterialEntity {
    @Id String id;
    String code;
    String name;
    String category;

    @Column(name = "created_at")
    Instant createdAt;
}

@Entity
@Table(name = "emission_factor")
class EmissionFactorEntity {
    @Id String id;

    @Column(name = "factor_code")
    String factorCode;

    @Column(name = "material_code")
    String materialCode;

    String name;

    @Column(name = "created_at")
    Instant createdAt;
}

@Entity
@Table(name = "factor_version")
class FactorVersionEntity {
    @Id String id;

    @Column(name = "factor_id")
    String factorId;

    int version;
    BigDecimal value;

    @Column(name = "activity_unit")
    String activityUnit;

    @Column(name = "co2e_unit")
    String co2eUnit;

    String source;
    String standard;
    String region;

    @Column(name = "reference_year")
    Integer referenceYear;

    @Column(name = "data_quality")
    String dataQuality;

    @Column(name = "density_kg_m3")
    BigDecimal densityKgM3;

    @Column(name = "licence_ref")
    String licenceRef;

    @Column(name = "content_hash")
    String contentHash;

    boolean approved;

    @Column(name = "created_at")
    Instant createdAt;
}

@Entity
@Table(name = "bom_line")
class BomLineEntity {
    @Id String id;

    @Column(name = "product_version_id")
    String productVersionId;

    @Column(name = "line_no")
    int lineNo;

    @Column(name = "material_id")
    String materialId;

    @Column(name = "part_name")
    String partName;

    @Column(name = "material_type")
    String materialType;

    BigDecimal quantity;
    String unit;

    @Column(name = "weight_kg_each")
    BigDecimal weightKgEach;

    @Column(name = "factor_version_id")
    String factorVersionId;

    String stage;

    @Column(name = "source_row")
    Integer sourceRow;

    @Column(name = "created_at")
    Instant createdAt;
}

@Entity
@Table(name = "process_route")
class ProcessRouteEntity {
    @Id String id;

    @Column(name = "product_id")
    String productId;

    @Column(name = "route_code")
    String routeCode;

    String version;
    boolean approved;

    @Column(name = "created_at")
    Instant createdAt;
}

@Entity
@Table(name = "route_step")
class RouteStepEntity {
    @Id String id;

    @Column(name = "route_id")
    String routeId;

    int sequence;

    @Column(name = "process_code")
    String processCode;

    String name;

    @Column(name = "standard_time_min")
    BigDecimal standardTimeMin;

    @Column(name = "energy_kwh_per_unit")
    BigDecimal energyKwhPerUnit;

    @Column(name = "created_at")
    Instant createdAt;
}

@Entity
@Table(name = "transport_activity")
class TransportActivityEntity {
    @Id String id;

    @Column(name = "product_version_id")
    String productVersionId;

    @Column(name = "material_id")
    String materialId;

    @Column(name = "supplier_id")
    String supplierId;

    String mode;

    @Column(name = "distance_km")
    BigDecimal distanceKm;

    @Column(name = "mass_kg")
    BigDecimal massKg;

    @Column(name = "load_factor")
    BigDecimal loadFactor;

    @Column(name = "factor_version_id")
    String factorVersionId;

    String source;
    boolean approved;

    @Column(name = "created_at")
    Instant createdAt;
}

@Entity
@Table(name = "material_process_mapping")
class MaterialProcessMappingEntity {
    @Id String id;

    @Column(name = "material_id")
    String materialId;

    @Column(name = "process_uuid")
    String processUuid;

    @Column(name = "reference_flow_uuid")
    String referenceFlowUuid;

    @Column(name = "openlca_unit")
    String openLcaUnit;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "conversion_rule", columnDefinition = "json")
    Object conversionRule;

    String region;

    @Column(name = "reference_year")
    Integer referenceYear;

    @Column(name = "database_version")
    String databaseVersion;

    String status;

    @Column(name = "reviewed_by")
    String reviewedBy;

    @Column(name = "created_at")
    Instant createdAt;
}

@Entity
@Table(name = "model_template_version")
class ModelTemplateVersionEntity {
    @Id String id;

    @Column(name = "template_id")
    String templateId;

    String version;

    @Column(name = "product_system_uuid")
    String productSystemUuid;

    @Column(name = "impact_method_uuid")
    String impactMethodUuid;

    @Column(name = "database_version")
    String databaseVersion;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "parameter_schema", columnDefinition = "json")
    Object parameterSchema;

    boolean approved;

    @Column(name = "created_at")
    Instant createdAt;
}
