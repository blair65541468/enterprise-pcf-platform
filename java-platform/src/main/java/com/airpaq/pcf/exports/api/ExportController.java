package com.airpaq.pcf.exports.api;

import com.airpaq.pcf.exports.application.ExportApplicationService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/calculations")
public class ExportController {

    private final ExportApplicationService exports;

    public ExportController(ExportApplicationService exports) {
        this.exports = exports;
    }

    @GetMapping("/{run_id}/export.json")
    ResponseEntity<byte[]> exportJson(@PathVariable("run_id") String runId) {
        return exports.json(runId);
    }

    @GetMapping("/{run_id}/export.xlsx")
    ResponseEntity<byte[]> exportExcel(@PathVariable("run_id") String runId) {
        return exports.excel(runId);
    }
}
