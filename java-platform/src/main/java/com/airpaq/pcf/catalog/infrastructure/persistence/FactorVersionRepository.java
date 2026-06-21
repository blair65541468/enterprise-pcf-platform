package com.airpaq.pcf.catalog.infrastructure.persistence;

import com.airpaq.pcf.catalog.domain.FactorVersion;
import org.springframework.data.jpa.repository.JpaRepository;

public interface FactorVersionRepository extends JpaRepository<FactorVersion, String> {}
