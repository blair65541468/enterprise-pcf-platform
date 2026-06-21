package com.airpaq.pcf.calculations.application;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CalculationRecoveryService {

    private final CalculationOperations calculations;

    public CalculationRecoveryService(CalculationOperations calculations) {
        this.calculations = calculations;
    }

    @Transactional
    public int recoverStale() {
        return calculations.recoverStale();
    }
}
