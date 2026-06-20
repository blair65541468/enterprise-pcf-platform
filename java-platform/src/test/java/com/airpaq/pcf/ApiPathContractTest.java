package com.airpaq.pcf;

import static org.assertj.core.api.Assertions.assertThat;

import com.airpaq.pcf.calculations.CalculationController;
import com.airpaq.pcf.catalog.AdminController;
import com.airpaq.pcf.health.HealthController;
import com.airpaq.pcf.imports.ImportController;
import com.airpaq.pcf.snapshots.SnapshotController;
import java.lang.reflect.Method;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.springframework.core.annotation.AnnotatedElementUtils;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;

class ApiPathContractTest {

    @Test
    void exposesTheFrozenTwentyOnePythonPaths() {
        var paths = new HashSet<String>();
        for (var controller :
                List.of(
                        HealthController.class,
                        ImportController.class,
                        SnapshotController.class,
                        CalculationController.class,
                        AdminController.class)) {
            collect(controller, paths);
        }
        assertThat(paths)
                .containsExactlyInAnyOrder(
                        "/health",
                        "/health/live",
                        "/health/ready",
                        "/health/openlca",
                        "/metrics",
                        "/v1/imports/excel",
                        "/v1/imports/{import_id}",
                        "/v1/products/{sku}/snapshots",
                        "/v1/calculations",
                        "/v1/calculations/{run_id}",
                        "/v1/calculations/{run_id}/contributions",
                        "/v1/calculations/{run_id}/submit",
                        "/v1/calculations/{run_id}/approve",
                        "/v1/calculations/{run_id}/reject",
                        "/v1/calculations/{run_id}/export.json",
                        "/v1/calculations/{run_id}/export.xlsx",
                        "/v1/calculations/{run_id}/audit-events",
                        "/v1/admin/factors/{factor_code}/approve",
                        "/v1/admin/mappings/materials",
                        "/v1/admin/products/{sku}/transport-activities",
                        "/v1/admin/products/{sku}/routes/{route_version}/approve",
                        "/v1/admin/model-templates");
    }

    private static void collect(Class<?> controller, Set<String> result) {
        var prefix = controller.getAnnotation(RequestMapping.class);
        var base = prefix == null || prefix.value().length == 0 ? "" : prefix.value()[0];
        for (Method method : controller.getDeclaredMethods()) {
            var get = AnnotatedElementUtils.findMergedAnnotation(method, GetMapping.class);
            if (get != null) result.add(base + value(get.value()));
            var post = AnnotatedElementUtils.findMergedAnnotation(method, PostMapping.class);
            if (post != null) result.add(base + value(post.value()));
        }
    }

    private static String value(String[] values) {
        return values.length == 0 ? "" : values[0];
    }
}
