package com.airpaq.pcf.imports;

import com.airpaq.pcf.infrastructure.api.ApiContracts.ImportJobOut;
import java.security.Principal;
import java.util.List;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/v1/imports")
public class ImportController {

    private final ExcelImportService service;

    public ImportController(ExcelImportService service) {
        this.service = service;
    }

    @PostMapping(path = "/excel", consumes = "multipart/form-data")
    @PreAuthorize("hasRole('data_submitter')")
    ImportJobOut importExcel(@RequestPart("files") List<MultipartFile> files, Principal principal) {
        return service.importFiles(files, principal.getName());
    }

    @GetMapping("/{import_id}")
    ImportJobOut get(@PathVariable("import_id") String importId) {
        return service.get(importId);
    }
}
