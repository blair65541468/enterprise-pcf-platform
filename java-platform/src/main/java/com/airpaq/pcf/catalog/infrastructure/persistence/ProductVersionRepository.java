package com.airpaq.pcf.catalog.infrastructure.persistence;

import com.airpaq.pcf.catalog.domain.ProductVersion;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ProductVersionRepository extends JpaRepository<ProductVersion, String> {
    Optional<ProductVersion> findFirstByProductIdOrderByVersionDesc(String productId);
}
