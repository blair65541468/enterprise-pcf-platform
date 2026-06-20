package com.airpaq.pcf.snapshots;

import com.airpaq.pcf.infrastructure.api.ApiContracts.SnapshotCreate;
import com.airpaq.pcf.infrastructure.api.ApiContracts.SnapshotOut;
import jakarta.validation.Valid;
import java.security.Principal;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/products")
public class SnapshotController {

    private final SnapshotService service;

    public SnapshotController(SnapshotService service) {
        this.service = service;
    }

    @PostMapping("/{sku}/snapshots")
    @PreAuthorize("hasAnyRole('data_submitter','admin')")
    SnapshotOut create(
            @PathVariable String sku,
            @Valid @RequestBody(required = false) SnapshotCreate request,
            Principal principal) {
        return service.create(
                sku,
                request == null ? new SnapshotCreate(null, null, null) : request,
                principal.getName());
    }
}
