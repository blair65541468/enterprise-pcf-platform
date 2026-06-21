package com.airpaq.pcf.imports.infrastructure.persistence;

import com.airpaq.pcf.imports.domain.ImportJob;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ImportJobRepository extends JpaRepository<ImportJob, String> {}
