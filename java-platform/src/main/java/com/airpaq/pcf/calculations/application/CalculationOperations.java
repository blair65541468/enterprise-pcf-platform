package com.airpaq.pcf.calculations.application;

import com.airpaq.pcf.calculations.api.dto.CalculationCreate;
import com.airpaq.pcf.calculations.api.dto.CalculationOut;
import com.airpaq.pcf.calculations.api.dto.ContributionOut;
import java.util.List;
import java.util.Map;

public interface CalculationOperations {
    CalculationOut create(CalculationCreate request, String actor, String requestId);

    CalculationOut get(String runId);

    List<ContributionOut> contributions(String runId);

    CalculationOut submit(String runId, String actor);

    CalculationOut approve(String runId, String actor);

    CalculationOut reject(String runId, String actor, String reason);

    boolean execute(String runId);

    boolean retry(String runId, RuntimeException exception);

    int recoverStale();

    List<Map<String, Object>> auditEvents(String runId);
}
