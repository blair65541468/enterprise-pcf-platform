package com.airpaq.pcf.snapshots.application;

import com.airpaq.pcf.snapshots.api.dto.SnapshotCreate;
import com.airpaq.pcf.snapshots.api.dto.SnapshotOut;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class SnapshotApplicationService {
    private final SnapshotOperations repository;

    public SnapshotApplicationService(SnapshotOperations repository) {
        this.repository = repository;
    }

    @Transactional
    public SnapshotOut create(String sku, SnapshotCreate request, String actor) {
        return repository.create(sku, request, actor);
    }
}
