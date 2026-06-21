package com.airpaq.pcf.imports.application;

import com.airpaq.pcf.imports.api.dto.ImportJobOut;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

@Service
public class ImportApplicationService {
    private final ImportOperations adapter;

    public ImportApplicationService(ImportOperations adapter) {
        this.adapter = adapter;
    }

    public ImportJobOut importFiles(List<MultipartFile> files, String actor) {
        return adapter.importFiles(files, actor);
    }

    public ImportJobOut get(String importId) {
        return adapter.get(importId);
    }
}
