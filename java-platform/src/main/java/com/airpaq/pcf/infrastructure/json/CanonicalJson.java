package com.airpaq.pcf.infrastructure.json;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import org.springframework.stereotype.Component;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.MapperFeature;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.SerializationFeature;

@Component
public class CanonicalJson {

    private final ObjectMapper mapper;

    public CanonicalJson(ObjectMapper source) {
        this.mapper =
                source.rebuild()
                        .enable(MapperFeature.SORT_PROPERTIES_ALPHABETICALLY)
                        .enable(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS)
                        .build();
    }

    public byte[] bytes(Object value) {
        try {
            return mapper.writeValueAsBytes(value);
        } catch (JacksonException exception) {
            throw new IllegalArgumentException("Value is not JSON serializable", exception);
        }
    }

    public String string(Object value) {
        return new String(bytes(value), StandardCharsets.UTF_8);
    }

    public String sha256(Object value) {
        return sha256(bytes(value));
    }

    public static String sha256(byte[] value) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value));
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is unavailable", exception);
        }
    }
}
