package com.airpaq.pcf.audit.application;

import java.util.Map;

public interface AuditOperations {
    void record(
            String actor,
            String action,
            String objectType,
            String objectId,
            String beforeHash,
            String afterHash,
            Map<String, ?> details);
}
