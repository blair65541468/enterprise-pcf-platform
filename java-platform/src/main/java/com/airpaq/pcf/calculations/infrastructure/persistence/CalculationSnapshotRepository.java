package com.airpaq.pcf.calculations.infrastructure.persistence;

import com.airpaq.pcf.calculations.domain.CalculationSnapshot;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CalculationSnapshotRepository extends JpaRepository<CalculationSnapshot, String> {}
