package com.airpaq.pcf.calculations;

import com.airpaq.pcf.infrastructure.api.ApiContracts.CalculationCreate;
import com.airpaq.pcf.infrastructure.api.ApiContracts.CalculationOut;
import com.airpaq.pcf.infrastructure.api.ApiContracts.ContributionOut;
import com.airpaq.pcf.infrastructure.api.ApiContracts.RejectionRequest;
import com.airpaq.pcf.infrastructure.web.RequestIdFilter;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import java.security.Principal;
import java.util.List;
import java.util.Map;
import org.springframework.http.ResponseEntity;
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

    private final CalculationService service;
    private final ExportService exports;

    public CalculationController(CalculationService service, ExportService exports) {
        this.service = service;
        this.exports = exports;
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

    @PostMapping("/{run_id}/submit")
    @PreAuthorize("hasRole('data_submitter')")
    CalculationOut submit(@PathVariable("run_id") String runId, Principal principal) {
        return service.submit(runId, principal.getName());
    }

    @PostMapping("/{run_id}/approve")
    @PreAuthorize("hasRole('lca_reviewer')")
    CalculationOut approve(@PathVariable("run_id") String runId, Principal principal) {
        return service.approve(runId, principal.getName());
    }

    @PostMapping("/{run_id}/reject")
    @PreAuthorize("hasRole('lca_reviewer')")
    CalculationOut reject(
            @PathVariable("run_id") String runId,
            @Valid @RequestBody RejectionRequest request,
            Principal principal) {
        return service.reject(runId, principal.getName(), request.reason());
    }

    @GetMapping("/{run_id}/export.json")
    ResponseEntity<byte[]> exportJson(@PathVariable("run_id") String runId) {
        return exports.json(runId);
    }

    @GetMapping("/{run_id}/export.xlsx")
    ResponseEntity<byte[]> exportExcel(@PathVariable("run_id") String runId) {
        return exports.excel(runId);
    }

    @GetMapping("/{run_id}/audit-events")
    List<Map<String, Object>> auditEvents(@PathVariable("run_id") String runId) {
        return service.auditEvents(runId);
    }
}
