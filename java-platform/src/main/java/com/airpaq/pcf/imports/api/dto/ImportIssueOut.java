package com.airpaq.pcf.imports.api.dto;

public record ImportIssueOut(
        String severity,
        String fileName,
        Integer rowNumber,
        String field,
        String code,
        String message) {}
