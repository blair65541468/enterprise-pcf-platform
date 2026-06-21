package com.airpaq.pcf.approvals.api;

import com.airpaq.pcf.approvals.application.ApprovalApplicationService;
import com.airpaq.pcf.calculations.api.dto.CalculationOut;
import com.airpaq.pcf.calculations.api.dto.RejectionRequest;
import jakarta.validation.Valid;
import java.security.Principal;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/calculations")
public class ApprovalController {

    private final ApprovalApplicationService approvals;

    public ApprovalController(ApprovalApplicationService approvals) {
        this.approvals = approvals;
    }

    @PostMapping("/{run_id}/submit")
    @PreAuthorize("hasRole('data_submitter')")
    CalculationOut submit(@PathVariable("run_id") String runId, Principal principal) {
        return approvals.submit(runId, principal.getName());
    }

    @PostMapping("/{run_id}/approve")
    @PreAuthorize("hasRole('lca_reviewer')")
    CalculationOut approve(@PathVariable("run_id") String runId, Principal principal) {
        return approvals.approve(runId, principal.getName());
    }

    @PostMapping("/{run_id}/reject")
    @PreAuthorize("hasRole('lca_reviewer')")
    CalculationOut reject(
            @PathVariable("run_id") String runId,
            @Valid @RequestBody RejectionRequest request,
            Principal principal) {
        return approvals.reject(runId, principal.getName(), request.reason());
    }
}
