package com.airpaq.pcf.infrastructure.config;

import java.net.URI;
import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("pcf")
public record PcfProperties(
        String role,
        boolean localAuthEnabled,
        OpenLca openlca,
        Storage storage,
        Calculation calculation,
        String appVersion,
        String gitCommit) {

    public record OpenLca(String engine, URI url, String apiToken, Duration timeout) {}

    public record Storage(
            URI endpoint, String accessKey, String secretKey, String bucket, String region) {}

    public record Calculation(Duration staleAfter, int maxAttempts) {}
}
