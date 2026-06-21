package com.airpaq.pcf.calculations.application;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CalculationExecutionService {

    private final CalculationOperations calculations;

    public CalculationExecutionService(CalculationOperations calculations) {
        this.calculations = calculations;
    }

    @Transactional
    public boolean execute(String runId) {
        return calculations.execute(runId);
    }

    @Transactional
    public boolean retry(String runId, RuntimeException exception) {
        return calculations.retry(runId, exception);
    }
}
