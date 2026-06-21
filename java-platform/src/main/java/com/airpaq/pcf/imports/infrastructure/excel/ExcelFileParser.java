package com.airpaq.pcf.imports.infrastructure.excel;

import java.io.ByteArrayInputStream;
import java.math.BigDecimal;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.CellType;
import org.apache.poi.ss.usermodel.DateUtil;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.stereotype.Component;

@Component
public class ExcelFileParser {

    public ParsedFile parse(String name, byte[] content) throws Exception {
        try (var workbook = new XSSFWorkbook(new ByteArrayInputStream(content))) {
            var sheet = workbook.getSheetAt(0);
            if (sheet.getPhysicalNumberOfRows() == 0) {
                return new ParsedFile(name, List.of(), List.of(), List.of());
            }
            var headerRow = sheet.getRow(sheet.getFirstRowNum());
            var headers = new ArrayList<String>();
            var duplicates = new ArrayList<String>();
            var seen = new HashMap<String, Integer>();
            for (var index = 0; index < headerRow.getLastCellNum(); index++) {
                var base = text(cellValue(headerRow.getCell(index)));
                var count = seen.merge(base, 1, Integer::sum);
                if (count > 1 && !base.isBlank()) duplicates.add(base);
                headers.add(count > 1 ? base + "__" + count : base);
            }
            var rows = new ArrayList<Map<String, Object>>();
            for (var rowIndex = sheet.getFirstRowNum() + 1;
                    rowIndex <= sheet.getLastRowNum();
                    rowIndex++) {
                var source = sheet.getRow(rowIndex);
                if (source == null) continue;
                var row = new LinkedHashMap<String, Object>();
                var hasValue = false;
                for (var column = 0; column < headers.size(); column++) {
                    var value = cellValue(source.getCell(column));
                    row.put(headers.get(column), value);
                    hasValue |= value != null && !String.valueOf(value).isBlank();
                }
                if (hasValue) rows.add(row);
            }
            return new ParsedFile(name, headers, rows, duplicates.stream().distinct().toList());
        }
    }

    private static Object cellValue(Cell cell) {
        if (cell == null) return null;
        if (cell.getCellType() == CellType.NUMERIC && DateUtil.isCellDateFormatted(cell)) {
            return cell.getLocalDateTimeCellValue()
                    .atOffset(ZoneOffset.UTC)
                    .format(DateTimeFormatter.ISO_OFFSET_DATE_TIME);
        }
        return switch (cell.getCellType()) {
            case STRING -> cell.getStringCellValue();
            case BOOLEAN -> cell.getBooleanCellValue();
            case NUMERIC -> BigDecimal.valueOf(cell.getNumericCellValue()).stripTrailingZeros();
            case FORMULA -> formulaValue(cell);
            case BLANK, _NONE, ERROR -> null;
        };
    }

    private static Object formulaValue(Cell cell) {
        return switch (cell.getCachedFormulaResultType()) {
            case STRING -> cell.getStringCellValue();
            case BOOLEAN -> cell.getBooleanCellValue();
            case NUMERIC -> BigDecimal.valueOf(cell.getNumericCellValue()).stripTrailingZeros();
            default -> null;
        };
    }

    private static String text(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }
}
