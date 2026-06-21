package com.airpaq.pcf.calculations.application;

import com.airpaq.pcf.calculations.api.dto.CalculationOut;
import com.airpaq.pcf.calculations.api.dto.ContributionOut;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class CalculationQueryService {

    private final CalculationOperations calculations;

    public CalculationQueryService(CalculationOperations calculations) {
        this.calculations = calculations;
    }

    public CalculationOut get(String runId) {
        return calculations.get(runId);
    }

    public List<ContributionOut> contributions(String runId) {
        return calculations.contributions(runId);
    }

    public List<Map<String, Object>> auditEvents(String runId) {
        return calculations.auditEvents(runId);
    }
}
