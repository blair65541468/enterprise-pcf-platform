package com.airpaq.pcf;

import com.airpaq.pcf.shared.config.PcfProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.scheduling.annotation.EnableScheduling;

@EnableScheduling
@EnableConfigurationProperties(PcfProperties.class)
@SpringBootApplication
public class PcfPlatformApplication {

    public static void main(String[] args) {
        SpringApplication.run(PcfPlatformApplication.class, args);
    }
}
