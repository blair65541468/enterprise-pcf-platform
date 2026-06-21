package com.airpaq.pcf.calculations.infrastructure.messaging;

import com.airpaq.pcf.calculations.application.CalculationExecutionService;
import org.slf4j.MDC;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.boot.autoconfigure.condition.ConditionalOnExpression;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnExpression("'${pcf.role:api}' == 'worker' or '${pcf.role:api}' == 'all'")
public class CalculationWorker {

    private final CalculationExecutionService calculations;

    public CalculationWorker(CalculationExecutionService calculations) {
        this.calculations = calculations;
    }

    @RabbitListener(queues = RabbitTopology.QUEUE)
    public void execute(CalculationMessage message) {
        MDC.put("request_id", message.requestId());
        MDC.put("calculation_id", message.runId());
        MDC.put("task_id", message.eventId());
        try {
            calculations.execute(message.runId());
        } catch (RuntimeException exception) {
            if (calculations.retry(message.runId(), exception)) {
                throw exception;
            }
        } finally {
            MDC.remove("request_id");
            MDC.remove("calculation_id");
            MDC.remove("task_id");
        }
    }
}
