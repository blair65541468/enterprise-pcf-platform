package com.airpaq.pcf.imports.application;

import com.airpaq.pcf.imports.api.dto.ImportJobOut;
import java.util.List;
import org.springframework.web.multipart.MultipartFile;

public interface ImportOperations {
    ImportJobOut importFiles(List<MultipartFile> files, String actor);

    ImportJobOut get(String importId);
}
