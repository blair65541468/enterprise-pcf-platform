@org.springframework.modulith.ApplicationModule(
        allowedDependencies = {
            "audit::application",
            "shared::config",
            "shared::json",
            "shared::storage",
            "shared::web"
        })
package com.airpaq.pcf.calculations;
