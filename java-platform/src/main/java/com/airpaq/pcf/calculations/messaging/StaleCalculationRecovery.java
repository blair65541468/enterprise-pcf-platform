package com.airpaq.pcf.calculations.messaging;

import com.airpaq.pcf.calculations.CalculationService;
import org.springframework.boot.autoconfigure.condition.ConditionalOnExpression;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnExpression("'${pcf.role:api}' == 'scheduler' or '${pcf.role:api}' == 'all'")
public class StaleCalculationRecovery {

    private final CalculationService calculations;

    public StaleCalculationRecovery(CalculationService calculations) {
        this.calculations = calculations;
    }

    @Scheduled(fixedDelayString = "${pcf.calculation.recovery-interval:60s}")
    public void recover() {
        calculations.recoverStale();
    }
}
