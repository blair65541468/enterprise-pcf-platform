package com.airpaq.pcf.approvals.application;

import com.airpaq.pcf.calculations.api.dto.CalculationOut;
import com.airpaq.pcf.calculations.application.CalculationApplicationService;
import org.springframework.stereotype.Service;

@Service
public class ApprovalApplicationService {

    private final CalculationApplicationService calculations;

    public ApprovalApplicationService(CalculationApplicationService calculations) {
        this.calculations = calculations;
    }

    public CalculationOut submit(String runId, String actor) {
        return calculations.submit(runId, actor);
    }

    public CalculationOut approve(String runId, String actor) {
        return calculations.approve(runId, actor);
    }

    public CalculationOut reject(String runId, String actor, String reason) {
        return calculations.reject(runId, actor, reason);
    }
}
