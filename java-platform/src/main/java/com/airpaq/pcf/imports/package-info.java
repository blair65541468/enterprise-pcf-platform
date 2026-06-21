@org.springframework.modulith.ApplicationModule(
        allowedDependencies = {
            "audit::application",
            "shared::json",
            "shared::storage",
            "shared::web"
        })
package com.airpaq.pcf.imports;
