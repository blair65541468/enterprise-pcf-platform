package com.airpaq.pcf.calculations.application;

import com.airpaq.pcf.calculations.api.dto.CalculationCreate;
import com.airpaq.pcf.calculations.api.dto.CalculationOut;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CalculationCommandService {

    private final CalculationOperations calculations;

    public CalculationCommandService(CalculationOperations calculations) {
        this.calculations = calculations;
    }

    @Transactional
    public CalculationOut create(CalculationCreate request, String actor, String requestId) {
        return calculations.create(request, actor, requestId);
    }

    @Transactional
    public CalculationOut submit(String runId, String actor) {
        return calculations.submit(runId, actor);
    }

    @Transactional
    public CalculationOut approve(String runId, String actor) {
        return calculations.approve(runId, actor);
    }

    @Transactional
    public CalculationOut reject(String runId, String actor, String reason) {
        return calculations.reject(runId, actor, reason);
    }
}
