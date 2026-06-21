package com.airpaq.pcf.calculations.application;

import com.airpaq.pcf.calculations.api.dto.CalculationCreate;
import com.airpaq.pcf.calculations.api.dto.CalculationOut;
import com.airpaq.pcf.calculations.api.dto.ContributionOut;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

@Service
public class CalculationApplicationService {
    private final CalculationCommandService commands;
    private final CalculationQueryService queries;
    private final CalculationExecutionService execution;
    private final CalculationRecoveryService recovery;

    public CalculationApplicationService(
            CalculationCommandService commands,
            CalculationQueryService queries,
            CalculationExecutionService execution,
            CalculationRecoveryService recovery) {
        this.commands = commands;
        this.queries = queries;
        this.execution = execution;
        this.recovery = recovery;
    }

    public CalculationOut create(CalculationCreate request, String actor, String requestId) {
        return commands.create(request, actor, requestId);
    }

    public CalculationOut get(String runId) {
        return queries.get(runId);
    }

    public List<ContributionOut> contributions(String runId) {
        return queries.contributions(runId);
    }

    public CalculationOut submit(String runId, String actor) {
        return commands.submit(runId, actor);
    }

    public CalculationOut approve(String runId, String actor) {
        return commands.approve(runId, actor);
    }

    public CalculationOut reject(String runId, String actor, String reason) {
        return commands.reject(runId, actor, reason);
    }

    public boolean execute(String runId) {
        return execution.execute(runId);
    }

    public boolean retry(String runId, RuntimeException exception) {
        return execution.retry(runId, exception);
    }

    public int recoverStale() {
        return recovery.recoverStale();
    }

    public List<Map<String, Object>> auditEvents(String runId) {
        return queries.auditEvents(runId);
    }
}
