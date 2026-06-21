package com.airpaq.pcf.imports.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "import_issue")
public class ImportIssue {
    @Id private String id;

    @Column(name = "import_job_id")
    private String importJobId;

    private String severity;

    @Column(name = "file_name")
    private String fileName;

    @Column(name = "row_number")
    private Integer rowNumber;

    private String field;
    private String code;
    private String message;

    @Column(name = "created_at")
    private Instant createdAt;

    protected ImportIssue() {}
}
