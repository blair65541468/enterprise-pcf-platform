package com.airpaq.pcf.audit.infrastructure.persistence;

import com.airpaq.pcf.audit.application.AuditOperations;
import java.time.Clock;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.ObjectMapper;

@Service
public class JdbcAuditRepository implements AuditOperations {

    private final JdbcTemplate jdbc;
    private final ObjectMapper objectMapper;
    private final Clock clock;

    @Autowired
    public JdbcAuditRepository(JdbcTemplate jdbc, ObjectMapper objectMapper) {
        this(jdbc, objectMapper, Clock.systemUTC());
    }

    JdbcAuditRepository(JdbcTemplate jdbc, ObjectMapper objectMapper, Clock clock) {
        this.jdbc = jdbc;
        this.objectMapper = objectMapper;
        this.clock = clock;
    }

    public void record(
            String actor,
            String action,
            String objectType,
            String objectId,
            String beforeHash,
            String afterHash,
            Map<String, ?> details) {
        try {
            jdbc.update(
                    """
                    insert into audit_event
                      (id, occurred_at, actor, action, object_type, object_id,
                       before_hash, after_hash, details)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?::json)
                    """,
                    UUID.randomUUID().toString(),
                    java.sql.Timestamp.from(Instant.now(clock)),
                    actor,
                    action,
                    objectType,
                    objectId,
                    beforeHash,
                    afterHash,
                    objectMapper.writeValueAsString(details == null ? Map.of() : details));
        } catch (JacksonException exception) {
            throw new IllegalArgumentException(
                    "Audit details are not JSON serializable", exception);
        }
    }
}
