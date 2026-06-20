package com.airpaq.pcf.calculations.messaging;

import com.airpaq.pcf.infrastructure.json.JsonSupport;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.boot.autoconfigure.condition.ConditionalOnExpression;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
@ConditionalOnExpression("'${pcf.role:api}' == 'scheduler' or '${pcf.role:api}' == 'all'")
public class OutboxPublisher {

    private final JdbcTemplate jdbc;
    private final JsonSupport json;
    private final RabbitTemplate rabbit;

    public OutboxPublisher(JdbcTemplate jdbc, JsonSupport json, RabbitTemplate rabbit) {
        this.jdbc = jdbc;
        this.json = json;
        this.rabbit = rabbit;
    }

    @Scheduled(fixedDelayString = "${pcf.outbox.poll-interval:2s}")
    @Transactional
    public void publish() {
        for (var event : claim()) {
            try {
                rabbit.invoke(
                        operations -> {
                            operations.convertAndSend(
                                    RabbitTopology.EXCHANGE,
                                    RabbitTopology.ROUTING_KEY,
                                    json.map(event.get("payload")));
                            operations.waitForConfirmsOrDie(5000);
                            return null;
                        });
                jdbc.update(
                        "update outbox_event set published_at = ? where id = ?",
                        java.sql.Timestamp.from(Instant.now()),
                        event.get("id"));
            } catch (RuntimeException exception) {
                jdbc.update(
                        """
                        update outbox_event set attempt_count = attempt_count + 1,
                          last_error = ? where id = ?
                        """,
                        truncate(exception.getMessage()),
                        event.get("id"));
                throw exception;
            }
        }
    }

    private List<Map<String, Object>> claim() {
        return jdbc.queryForList(
                """
                select id, payload from outbox_event
                where published_at is null
                order by created_at
                for update skip locked limit 50
                """);
    }

    private static String truncate(String value) {
        if (value == null) return "RabbitMQ publish failed";
        return value.length() <= 4000 ? value : value.substring(0, 4000);
    }
}
