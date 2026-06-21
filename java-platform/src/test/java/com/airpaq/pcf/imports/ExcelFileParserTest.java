package com.airpaq.pcf.imports;

import static org.assertj.core.api.Assertions.assertThat;

import com.airpaq.pcf.imports.infrastructure.excel.ExcelFileParser;
import com.airpaq.pcf.imports.infrastructure.excel.ExcelFileType;
import com.airpaq.pcf.imports.infrastructure.excel.ExcelFileTypeDetector;
import java.io.ByteArrayOutputStream;
import java.math.BigDecimal;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.junit.jupiter.api.Test;

class ExcelFileParserTest {

    private final ExcelFileParser parser = new ExcelFileParser();
    private final ExcelFileTypeDetector detector = new ExcelFileTypeDetector();

    @Test
    void parsesRowsAndRenamesDuplicateHeaders() throws Exception {
        byte[] content;
        try (var workbook = new XSSFWorkbook();
                var output = new ByteArrayOutputStream()) {
            var sheet = workbook.createSheet("Factors");
            var headers = sheet.createRow(0);
            headers.createCell(0).setCellValue("Factor Value");
            headers.createCell(1).setCellValue("Unit");
            headers.createCell(2).setCellValue("Unit");
            var row = sheet.createRow(1);
            row.createCell(0).setCellValue(7.525);
            row.createCell(1).setCellValue("kg CO2e");
            workbook.write(output);
            content = output.toByteArray();
        }

        var parsed = parser.parse("Factors.xlsx", content);

        assertThat(parsed.headers()).containsExactly("Factor Value", "Unit", "Unit__2");
        assertThat(parsed.duplicateHeaders()).containsExactly("Unit");
        assertThat(parsed.rows()).hasSize(1);
        assertThat(parsed.rows().getFirst().get("Factor Value")).isEqualTo(new BigDecimal("7.525"));
        assertThat(detector.detect(parsed)).isEqualTo(ExcelFileType.FACTOR);
    }
}
