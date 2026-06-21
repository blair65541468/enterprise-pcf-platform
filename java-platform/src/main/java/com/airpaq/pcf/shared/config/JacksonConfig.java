package com.airpaq.pcf.shared.config;

import java.math.BigDecimal;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import tools.jackson.databind.JacksonModule;
import tools.jackson.databind.module.SimpleModule;
import tools.jackson.databind.ser.std.ToStringSerializer;

@Configuration
public class JacksonConfig {

    @Bean
    JacksonModule decimalAsStringModule() {
        var module = new SimpleModule("python-compatible-decimal");
        module.addSerializer(BigDecimal.class, ToStringSerializer.instance);
        return module;
    }
}
