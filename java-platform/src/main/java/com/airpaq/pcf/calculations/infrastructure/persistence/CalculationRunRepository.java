package com.airpaq.pcf.calculations.infrastructure.persistence;

import com.airpaq.pcf.calculations.domain.CalculationRun;
import jakarta.persistence.LockModeType;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface CalculationRunRepository extends JpaRepository<CalculationRun, String> {
    Optional<CalculationRun> findByIdempotencyKey(String idempotencyKey);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select run from CalculationRun run where run.id = :id")
    Optional<CalculationRun> findByIdForUpdate(@Param("id") String id);
}
