package com.airpaq.pcf.calculations.api.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record RejectionRequest(@NotBlank @Size(min = 5, max = 2000) String reason) {}
