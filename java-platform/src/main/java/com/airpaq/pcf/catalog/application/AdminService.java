package com.airpaq.pcf.catalog.application;

import com.airpaq.pcf.catalog.api.dto.FactorApproval;
import com.airpaq.pcf.catalog.api.dto.MappingCreate;
import com.airpaq.pcf.catalog.api.dto.ModelTemplateCreate;
import com.airpaq.pcf.catalog.api.dto.TransportCreate;
import java.util.Map;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional
public class AdminService {
    private final CatalogOperations repository;

    public AdminService(CatalogOperations repository) {
        this.repository = repository;
    }

    public Map<String, Object> approveFactor(String code, FactorApproval request, String actor) {
        return repository.approveFactor(code, request, actor);
    }

    public Map<String, Object> createMapping(MappingCreate request, String actor) {
        return repository.createMapping(request, actor);
    }

    public Map<String, Object> createTransport(String sku, TransportCreate request, String actor) {
        return repository.createTransport(sku, request, actor);
    }

    public Map<String, Object> approveRoute(String sku, String version, String actor) {
        return repository.approveRoute(sku, version, actor);
    }

    public Map<String, Object> createTemplate(ModelTemplateCreate request, String actor) {
        return repository.createTemplate(request, actor);
    }
}
