package com.airpaq.pcf.calculations.infrastructure.messaging;

import com.airpaq.pcf.calculations.application.CalculationRecoveryService;
import org.springframework.boot.autoconfigure.condition.ConditionalOnExpression;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnExpression("'${pcf.role:api}' == 'scheduler' or '${pcf.role:api}' == 'all'")
public class StaleCalculationRecovery {

    private final CalculationRecoveryService calculations;

    public StaleCalculationRecovery(CalculationRecoveryService calculations) {
        this.calculations = calculations;
    }

    @Scheduled(fixedDelayString = "${pcf.calculation.recovery-interval:60s}")
    public void recover() {
        calculations.recoverStale();
    }
}
