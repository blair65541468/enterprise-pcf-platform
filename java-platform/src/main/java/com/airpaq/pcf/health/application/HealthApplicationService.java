package com.airpaq.pcf.health.application;

import com.airpaq.pcf.calculations.domain.CalculationEngine;
import java.util.Map;
import org.springframework.stereotype.Service;

@Service
public class HealthApplicationService {

    private final HealthReadiness readiness;
    private final CalculationEngine engine;

    public HealthApplicationService(HealthReadiness readiness, CalculationEngine engine) {
        this.readiness = readiness;
        this.engine = engine;
    }

    public Map<String, String> health() {
        readiness.database();
        return Map.of("status", "ok");
    }

    public Map<String, Object> ready() {
        return readiness.all();
    }

    public Map<String, Object> openLca() {
        return engine.health();
    }
}
