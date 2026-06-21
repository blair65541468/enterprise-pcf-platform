package com.airpaq.pcf.snapshots.application;

import com.airpaq.pcf.snapshots.api.dto.SnapshotCreate;
import com.airpaq.pcf.snapshots.api.dto.SnapshotOut;

public interface SnapshotOperations {
    SnapshotOut create(String sku, SnapshotCreate request, String actor);
}
