package com.airpaq.pcf.health.api;

import com.airpaq.pcf.health.application.HealthApplicationService;
import io.micrometer.prometheusmetrics.PrometheusMeterRegistry;
import java.util.Map;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {

    private final HealthApplicationService health;
    private final PrometheusMeterRegistry prometheus;

    public HealthController(HealthApplicationService health, PrometheusMeterRegistry prometheus) {
        this.health = health;
        this.prometheus = prometheus;
    }

    @GetMapping("/health")
    Map<String, String> health() {
        return health.health();
    }

    @GetMapping("/health/live")
    Map<String, String> live() {
        return Map.of("status", "ok");
    }

    @GetMapping("/health/ready")
    Map<String, Object> ready() {
        return health.ready();
    }

    @GetMapping("/health/openlca")
    Map<String, Object> openLca() {
        return health.openLca();
    }

    @GetMapping(value = "/metrics", produces = MediaType.TEXT_PLAIN_VALUE)
    String metrics() {
        return prometheus.scrape();
    }
}
