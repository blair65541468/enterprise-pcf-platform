package com.airpaq.pcf.calculations.infrastructure.messaging;

import com.airpaq.pcf.calculations.infrastructure.persistence.OutboxEventRepository;
import java.time.Instant;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.boot.autoconfigure.condition.ConditionalOnExpression;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
@ConditionalOnExpression("'${pcf.role:api}' == 'scheduler' or '${pcf.role:api}' == 'all'")
public class OutboxPublisher {

    private final OutboxEventRepository events;
    private final RabbitTemplate rabbit;

    public OutboxPublisher(OutboxEventRepository events, RabbitTemplate rabbit) {
        this.events = events;
        this.rabbit = rabbit;
    }

    @Scheduled(fixedDelayString = "${pcf.outbox.poll-interval:2s}")
    @Transactional
    public void publish() {
        for (var event : events.claimUnpublished()) {
            try {
                rabbit.invoke(
                        operations -> {
                            operations.convertAndSend(
                                    RabbitTopology.EXCHANGE,
                                    RabbitTopology.ROUTING_KEY,
                                    event.payload());
                            operations.waitForConfirmsOrDie(5000);
                            return null;
                        });
                event.markPublished(Instant.now());
            } catch (RuntimeException exception) {
                event.markFailed(truncate(exception.getMessage()));
                throw exception;
            }
        }
    }

    private static String truncate(String value) {
        if (value == null) return "RabbitMQ publish failed";
        return value.length() <= 4000 ? value : value.substring(0, 4000);
    }
}
