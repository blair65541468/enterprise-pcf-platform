package com.airpaq.pcf.imports;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

final class ImportEntities {
    private ImportEntities() {}
}

@Entity
@Table(name = "import_job")
class ImportJobEntity {
    @Id String id;
    String status;

    @Column(name = "created_by")
    String createdBy;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "file_manifest", columnDefinition = "json")
    Object fileManifest;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "json")
    Object summary;

    @Column(name = "completed_at")
    Instant completedAt;

    @Column(name = "created_at")
    Instant createdAt;
}

@Entity
@Table(name = "import_issue")
class ImportIssueEntity {
    @Id String id;

    @Column(name = "import_job_id")
    String importJobId;

    String severity;

    @Column(name = "file_name")
    String fileName;

    @Column(name = "row_number")
    Integer rowNumber;

    String field;
    String code;
    String message;

    @Column(name = "created_at")
    Instant createdAt;
}
