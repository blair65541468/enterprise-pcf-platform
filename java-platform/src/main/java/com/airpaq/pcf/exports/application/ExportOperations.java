package com.airpaq.pcf.exports.application;

import org.springframework.http.ResponseEntity;

public interface ExportOperations {
    ResponseEntity<byte[]> json(String runId);

    ResponseEntity<byte[]> excel(String runId);
}
