package com.airpaq.pcf.health;

import com.airpaq.pcf.calculations.CalculationEngine;
import io.micrometer.prometheusmetrics.PrometheusMeterRegistry;
import java.util.LinkedHashMap;
import java.util.Map;
import javax.sql.DataSource;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {

    private final JdbcTemplate jdbc;
    private final ConnectionFactory rabbit;
    private final CalculationEngine engine;
    private final PrometheusMeterRegistry prometheus;

    public HealthController(
            DataSource dataSource,
            ConnectionFactory rabbit,
            CalculationEngine engine,
            PrometheusMeterRegistry prometheus) {
        this.jdbc = new JdbcTemplate(dataSource);
        this.rabbit = rabbit;
        this.engine = engine;
        this.prometheus = prometheus;
    }

    @GetMapping("/health")
    Map<String, String> health() {
        jdbc.queryForObject("select 1", Integer.class);
        return Map.of("status", "ok");
    }

    @GetMapping("/health/live")
    Map<String, String> live() {
        return Map.of("status", "ok");
    }

    @GetMapping("/health/ready")
    Map<String, Object> ready() {
        jdbc.queryForObject("select 1", Integer.class);
        try (var ignored = rabbit.createConnection()) {
            var checks = new LinkedHashMap<String, Object>();
            checks.put("database", Map.of("status", "ok"));
            checks.put("task_broker", Map.of("status", "ok"));
            return Map.of("status", "ok", "checks", checks);
        }
    }

    @GetMapping("/health/openlca")
    Map<String, Object> openLca() {
        return engine.health();
    }

    @GetMapping(value = "/metrics", produces = MediaType.TEXT_PLAIN_VALUE)
    String metrics() {
        return prometheus.scrape();
    }
}
