package com.airpaq.pcf.infrastructure.storage;

public interface ObjectStorage {
    void put(String key, byte[] data, String contentType);

    byte[] get(String key);

    void health();
}
