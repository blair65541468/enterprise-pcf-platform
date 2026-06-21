package com.airpaq.pcf.shared.config;

import io.swagger.v3.oas.models.media.ArraySchema;
import io.swagger.v3.oas.models.media.ObjectSchema;
import io.swagger.v3.oas.models.media.Schema;
import io.swagger.v3.oas.models.media.StringSchema;
import org.springdoc.core.customizers.OpenApiCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {

    @Bean
    OpenApiCustomizer pythonCompatibilitySchemas() {
        return openApi -> {
            var components = openApi.getComponents();
            components.addSchemas(
                    "ValidationError",
                    new ObjectSchema()
                            .addProperty("loc", new ArraySchema().items(new Schema<>()))
                            .addProperty("msg", new StringSchema())
                            .addProperty("type", new StringSchema()));
            components.addSchemas(
                    "HTTPValidationError",
                    new ObjectSchema()
                            .addProperty(
                                    "detail",
                                    new ArraySchema()
                                            .items(
                                                    new Schema<>()
                                                            .$ref(
                                                                    "#/components/schemas/ValidationError"))));
            components.addSchemas(
                    "Body_import_excel_v1_imports_excel_post",
                    new ObjectSchema()
                            .addProperty(
                                    "files",
                                    new ArraySchema().items(new StringSchema().format("binary"))));
        };
    }
}
