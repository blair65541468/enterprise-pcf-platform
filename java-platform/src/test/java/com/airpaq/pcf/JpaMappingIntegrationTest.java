package com.airpaq.pcf;

import static org.assertj.core.api.Assertions.assertThat;

import com.airpaq.pcf.calculations.infrastructure.persistence.CalculationRunRepository;
import com.airpaq.pcf.catalog.infrastructure.persistence.ProductRepository;
import com.airpaq.pcf.imports.infrastructure.persistence.ImportJobRepository;
import com.airpaq.pcf.shared.storage.ObjectStorage;
import jakarta.persistence.EntityManagerFactory;
import javax.sql.DataSource;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.testcontainers.containers.PostgreSQLContainer;

@SpringBootTest(
        webEnvironment = SpringBootTest.WebEnvironment.NONE,
        properties = {
            "pcf.role=api",
            "spring.flyway.enabled=false",
            "spring.jpa.hibernate.ddl-auto=validate",
            "spring.rabbitmq.listener.simple.auto-startup=false"
        })
class JpaMappingIntegrationTest {

    private static final PostgreSQLContainer<?> POSTGRES =
            new PostgreSQLContainer<>("postgres:16-alpine");

    static {
        POSTGRES.start();
        Flyway.configure()
                .dataSource(POSTGRES.getJdbcUrl(), POSTGRES.getUsername(), POSTGRES.getPassword())
                .load()
                .migrate();
    }

    @DynamicPropertySource
    static void postgresProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", POSTGRES::getUsername);
        registry.add("spring.datasource.password", POSTGRES::getPassword);
    }

    @MockitoBean ObjectStorage objectStorage;

    @Autowired EntityManagerFactory entityManagerFactory;
    @Autowired DataSource dataSource;
    @Autowired ProductRepository products;
    @Autowired ImportJobRepository imports;
    @Autowired CalculationRunRepository calculations;

    @Test
    void validatesFlywayAndJpaMappingsAgainstPostgresql() {
        var flyway = Flyway.configure().dataSource(dataSource).load();

        assertThat(flyway.info().current().getVersion().getVersion()).isEqualTo("3");
        assertThat(entityManagerFactory.getMetamodel().getEntities())
                .hasSizeGreaterThanOrEqualTo(18);
        assertThat(products.count()).isZero();
        assertThat(imports.count()).isZero();
        assertThat(calculations.count()).isZero();
    }
}
