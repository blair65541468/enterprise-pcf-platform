package com.airpaq.pcf.catalog;

import com.airpaq.pcf.infrastructure.api.ApiContracts.FactorApproval;
import com.airpaq.pcf.infrastructure.api.ApiContracts.MappingCreate;
import com.airpaq.pcf.infrastructure.api.ApiContracts.ModelTemplateCreate;
import com.airpaq.pcf.infrastructure.api.ApiContracts.TransportCreate;
import jakarta.validation.Valid;
import java.security.Principal;
import java.util.Map;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/admin")
@PreAuthorize("hasRole('lca_reviewer')")
public class AdminController {

    private final AdminService service;

    public AdminController(AdminService service) {
        this.service = service;
    }

    @PostMapping("/factors/{factor_code}/approve")
    Map<String, Object> approveFactor(
            @PathVariable("factor_code") String factorCode,
            @Valid @RequestBody FactorApproval request,
            Principal principal) {
        return service.approveFactor(factorCode, request, principal.getName());
    }

    @PostMapping("/mappings/materials")
    Map<String, Object> mapping(@Valid @RequestBody MappingCreate request, Principal principal) {
        return service.createMapping(request, principal.getName());
    }

    @PostMapping("/products/{sku}/transport-activities")
    Map<String, Object> transport(
            @PathVariable String sku,
            @Valid @RequestBody TransportCreate request,
            Principal principal) {
        return service.createTransport(sku, request, principal.getName());
    }

    @PostMapping("/products/{sku}/routes/{route_version}/approve")
    Map<String, Object> approveRoute(
            @PathVariable String sku,
            @PathVariable("route_version") String routeVersion,
            Principal principal) {
        return service.approveRoute(sku, routeVersion, principal.getName());
    }

    @PostMapping("/model-templates")
    Map<String, Object> template(
            @Valid @RequestBody ModelTemplateCreate request, Principal principal) {
        return service.createTemplate(request, principal.getName());
    }
}
