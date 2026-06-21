package com.airpaq.pcf.catalog.application;

import com.airpaq.pcf.catalog.api.dto.FactorApproval;
import com.airpaq.pcf.catalog.api.dto.MappingCreate;
import com.airpaq.pcf.catalog.api.dto.ModelTemplateCreate;
import com.airpaq.pcf.catalog.api.dto.TransportCreate;
import java.util.Map;

public interface CatalogOperations {
    Map<String, Object> approveFactor(String code, FactorApproval request, String actor);

    Map<String, Object> createMapping(MappingCreate request, String actor);

    Map<String, Object> createTransport(String sku, TransportCreate request, String actor);

    Map<String, Object> approveRoute(String sku, String version, String actor);

    Map<String, Object> createTemplate(ModelTemplateCreate request, String actor);
}
