package com.airpaq.pcf.shared.json;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.LinkedHashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.ObjectMapper;

class CanonicalJsonTest {

    private final CanonicalJson canonical = new CanonicalJson(new ObjectMapper());

    @Test
    void sortsObjectKeysAndProducesStableSha256() {
        var first = new LinkedHashMap<String, Object>();
        first.put("z", 1);
        first.put("a", Map.of("b", 2, "a", 1));

        var second = new LinkedHashMap<String, Object>();
        second.put("a", Map.of("a", 1, "b", 2));
        second.put("z", 1);

        assertThat(canonical.string(first)).isEqualTo("{\"a\":{\"a\":1,\"b\":2},\"z\":1}");
        assertThat(canonical.sha256(first)).isEqualTo(canonical.sha256(second));
    }
}
