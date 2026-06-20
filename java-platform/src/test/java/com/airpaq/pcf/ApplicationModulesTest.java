package com.airpaq.pcf;

import org.junit.jupiter.api.Test;
import org.springframework.modulith.core.ApplicationModules;

class ApplicationModulesTest {

    @Test
    void verifiesModuleDependenciesAndCycles() {
        ApplicationModules.of(PcfPlatformApplication.class).verify();
    }
}
