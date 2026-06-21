package com.airpaq.pcf.health.application;

import java.util.Map;

public interface HealthReadiness {
    void database();

    Map<String, Object> all();
}
