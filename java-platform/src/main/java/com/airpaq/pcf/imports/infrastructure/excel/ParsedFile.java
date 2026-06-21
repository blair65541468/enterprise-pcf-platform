package com.airpaq.pcf.imports.infrastructure.excel;

import java.util.List;
import java.util.Map;

public record ParsedFile(
        String name,
        List<String> headers,
        List<Map<String, Object>> rows,
        List<String> duplicateHeaders) {}
