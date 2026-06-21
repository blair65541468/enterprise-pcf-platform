package com.airpaq.pcf.imports.api.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(enumAsRef = true)
public enum ImportStatus {
    uploaded,
    processing,
    validated,
    failed
}
