package com.airpaq.pcf.health.infrastructure;

import com.airpaq.pcf.health.application.HealthReadiness;
import java.util.LinkedHashMap;
import java.util.Map;
import javax.sql.DataSource;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

@Component
public class ReadinessProbe implements HealthReadiness {

    private final JdbcTemplate jdbc;
    private final ConnectionFactory rabbit;

    public ReadinessProbe(DataSource dataSource, ConnectionFactory rabbit) {
        this.jdbc = new JdbcTemplate(dataSource);
        this.rabbit = rabbit;
    }

    public void database() {
        jdbc.queryForObject("select 1", Integer.class);
    }

    public Map<String, Object> all() {
        database();
        try (var ignored = rabbit.createConnection()) {
            var checks = new LinkedHashMap<String, Object>();
            checks.put("database", Map.of("status", "ok"));
            checks.put("task_broker", Map.of("status", "ok"));
            return Map.of("status", "ok", "checks", checks);
        }
    }
}
