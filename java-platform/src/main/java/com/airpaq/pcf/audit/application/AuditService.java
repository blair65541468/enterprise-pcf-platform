package com.airpaq.pcf.audit.application;

import java.util.Map;
import org.springframework.stereotype.Service;

@Service
public class AuditService {
    private final AuditOperations repository;

    public AuditService(AuditOperations repository) {
        this.repository = repository;
    }

    public void record(
            String actor,
            String action,
            String objectType,
            String objectId,
            String beforeHash,
            String afterHash,
            Map<String, ?> details) {
        repository.record(actor, action, objectType, objectId, beforeHash, afterHash, details);
    }
}
