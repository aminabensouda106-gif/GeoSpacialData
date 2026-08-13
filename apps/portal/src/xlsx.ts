import ExcelJS from "exceljs";

export interface XlsxColumn {
  header: string;
  key: string;
  /** Numeric columns get right-aligned, fixed-decimal number formatting
   *  instead of Excel showing the raw floating-point value. */
  numeric?: boolean;
  decimals?: number;
}

const HEADER_FILL = "FF2E6B49"; // --field
const HEADER_BORDER = "FF1F4E35"; // --field-dark
const STRIPE_FILL = "FFF3F4EC"; // near --paper-dim
const ROW_BORDER = "FFE3E6D7"; // --paper-dim

/** Builds a real, formatted .xlsx (styled header, frozen header row,
 *  auto-filter, zebra striping, fixed-decimal numbers) and triggers a
 *  browser download — a plain CSV can't carry any of that formatting. */
export async function downloadXlsx(
  filename: string,
  sheetName: string,
  columns: XlsxColumn[],
  rows: Record<string, unknown>[]
) {
  const workbook = new ExcelJS.Workbook();
  workbook.creator = "GeoData Platform";
  workbook.created = new Date();

  const sheet = workbook.addWorksheet(sheetName.slice(0, 31) || "Sheet1", {
    views: [{ state: "frozen", ySplit: 1 }],
  });

  sheet.columns = columns.map((c) => ({
    header: c.header,
    key: c.key,
    width: Math.min(40, Math.max(12, c.header.length + 4)),
  }));

  for (const r of rows) {
    const record: Record<string, unknown> = {};
    for (const c of columns) {
      const raw = r[c.key];
      const isBlank = raw === undefined || raw === null || raw === "";
      record[c.key] = c.numeric && !isBlank ? Number(raw) : isBlank ? "" : raw;
    }
    sheet.addRow(record);
  }

  columns.forEach((c, i) => {
    if (c.numeric) {
      const decimals = c.decimals ?? 3;
      sheet.getColumn(i + 1).numFmt = "0." + "0".repeat(decimals);
      sheet.getColumn(i + 1).alignment = { horizontal: "right" };
    }
  });

  const headerRow = sheet.getRow(1);
  headerRow.height = 20;
  headerRow.eachCell((cell) => {
    cell.font = { bold: true, color: { argb: "FFFFFFFF" }, size: 11 };
    cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: HEADER_FILL } };
    cell.alignment = { vertical: "middle", horizontal: "center" };
    cell.border = { bottom: { style: "thin", color: { argb: HEADER_BORDER } } };
  });

  sheet.eachRow((row, rowNumber) => {
    if (rowNumber === 1) return;
    const isEven = rowNumber % 2 === 0;
    row.eachCell({ includeEmpty: true }, (cell) => {
      cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: isEven ? STRIPE_FILL : "FFFFFFFF" } };
      cell.border = { bottom: { style: "thin", color: { argb: ROW_BORDER } } };
      if (!cell.font) cell.font = { size: 11 };
    });
  });

  sheet.autoFilter = { from: { row: 1, column: 1 }, to: { row: 1, column: columns.length } };

  const buffer = await workbook.xlsx.writeBuffer();
  const blob = new Blob([buffer], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(".xlsx") ? filename : `${filename}.xlsx`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
