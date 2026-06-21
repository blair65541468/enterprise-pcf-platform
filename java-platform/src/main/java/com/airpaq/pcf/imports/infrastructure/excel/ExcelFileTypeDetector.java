package com.airpaq.pcf.imports.infrastructure.excel;

import org.springframework.stereotype.Component;

@Component
public class ExcelFileTypeDetector {

    public ExcelFileType detect(ParsedFile file) {
        if (file.headers().stream().anyMatch(value -> value.contains("Factor Value"))) {
            return ExcelFileType.FACTOR;
        }
        var name = file.name();
        if (name.contains("Product_Master")) return ExcelFileType.PRODUCT;
        if (name.contains("Product_BOM")) return ExcelFileType.BOM;
        if (name.contains("Process_Routing")) return ExcelFileType.ROUTE;
        if (name.contains("Equipment_Ledger")) return ExcelFileType.EQUIPMENT;
        if (name.contains("Supplier_Profile")) return ExcelFileType.SUPPLIER;
        if (name.contains("Capability_Baseline")) return ExcelFileType.CAPABILITY_BASELINE;
        return ExcelFileType.UNKNOWN;
    }
}
