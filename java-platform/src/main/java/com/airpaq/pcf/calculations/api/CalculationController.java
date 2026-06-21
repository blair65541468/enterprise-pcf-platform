package com.airpaq.pcf.calculations.api;

import com.airpaq.pcf.calculations.api.dto.CalculationCreate;
import com.airpaq.pcf.calculations.api.dto.CalculationOut;
import com.airpaq.pcf.calculations.api.dto.ContributionOut;
import com.airpaq.pcf.calculations.application.CalculationApplicationService;
import com.airpaq.pcf.shared.web.RequestIdFilter;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import java.security.Principal;
import java.util.List;
import java.util.Map;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/calculations")
public class CalculationController {

    private final CalculationApplicationService service;

    public CalculationController(CalculationApplicationService service) {
        this.service = service;
    }

    @PostMapping
    @PreAuthorize("hasRole('data_submitter')")
    CalculationOut create(
            @Valid @RequestBody CalculationCreate request,
            Principal principal,
            HttpServletRequest servletRequest) {
        return service.create(
                request,
                principal.getName(),
                String.valueOf(servletRequest.getAttribute(RequestIdFilter.REQUEST_ID_ATTRIBUTE)));
    }

    @GetMapping("/{run_id}")
    CalculationOut get(@PathVariable("run_id") String runId) {
        return service.get(runId);
    }

    @GetMapping("/{run_id}/contributions")
    List<ContributionOut> contributions(@PathVariable("run_id") String runId) {
        return service.contributions(runId);
    }

    @GetMapping("/{run_id}/audit-events")
    List<Map<String, Object>> auditEvents(@PathVariable("run_id") String runId) {
        return service.auditEvents(runId);
    }
}
