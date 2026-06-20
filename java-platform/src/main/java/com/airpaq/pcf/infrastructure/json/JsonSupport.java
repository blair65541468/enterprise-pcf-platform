package com.airpaq.pcf.infrastructure.json;

import java.util.List;
import java.util.Map;
import org.postgresql.util.PGobject;
import org.springframework.stereotype.Component;
import tools.jackson.core.JacksonException;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.ObjectMapper;

@Component
public class JsonSupport {

    private final ObjectMapper mapper;

    public JsonSupport(ObjectMapper mapper) {
        this.mapper = mapper;
    }

    public Map<String, Object> map(Object value) {
        if (value == null) return Map.of();
        if (value instanceof Map<?, ?> raw) {
            return mapper.convertValue(raw, new TypeReference<>() {});
        }
        return readMap(text(value));
    }

    public List<Map<String, Object>> list(Object value) {
        if (value == null) return List.of();
        if (value instanceof List<?> raw) {
            return mapper.convertValue(raw, new TypeReference<>() {});
        }
        try {
            return mapper.readValue(text(value), new TypeReference<>() {});
        } catch (JacksonException exception) {
            throw new IllegalArgumentException("Invalid JSON array", exception);
        }
    }

    public String write(Object value) {
        try {
            return mapper.writeValueAsString(value);
        } catch (JacksonException exception) {
            throw new IllegalArgumentException("Value is not JSON serializable", exception);
        }
    }

    private Map<String, Object> readMap(String value) {
        try {
            return mapper.readValue(value, new TypeReference<>() {});
        } catch (JacksonException exception) {
            throw new IllegalArgumentException("Invalid JSON object", exception);
        }
    }

    private static String text(Object value) {
        return value instanceof PGobject pg ? pg.getValue() : String.valueOf(value);
    }
}
