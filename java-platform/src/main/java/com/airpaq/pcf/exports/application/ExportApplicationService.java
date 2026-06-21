package com.airpaq.pcf.exports.application;

import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;

@Service
public class ExportApplicationService {
    private final ExportOperations adapter;

    public ExportApplicationService(ExportOperations adapter) {
        this.adapter = adapter;
    }

    public ResponseEntity<byte[]> json(String runId) {
        return adapter.json(runId);
    }

    public ResponseEntity<byte[]> excel(String runId) {
        return adapter.excel(runId);
    }
}
