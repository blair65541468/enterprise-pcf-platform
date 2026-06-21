package com.airpaq.pcf.catalog.infrastructure.persistence;

import com.airpaq.pcf.catalog.domain.Product;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ProductRepository extends JpaRepository<Product, String> {
    Optional<Product> findBySku(String sku);
}
