import fs from "node:fs/promises";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { SpreadsheetFile, Workbook } = require("@oai/artifact-tool");

const root = process.cwd();
const payloadPath = `${root}/tmp_workbook/company_three_table_data.json`;
const outputDir = `${root}/final/三表抽取_仿样式`;
const previewDir = `${root}/tmp_workbook/company_three_table_previews`;

function valueForCell(value) {
  if (value === null || value === undefined || value === "") return "";
  if (typeof value === "number") return value;
  const s = String(value).trim();
  if (s === "") return "";
  if (/^\d+(\.\d+)?$/.test(s) && !/^0\d/.test(s)) return Number(s);
  return s;
}

function colLetter(num) {
  let s = "";
  while (num > 0) {
    const m = (num - 1) % 26;
    s = String.fromCharCode(65 + m) + s;
    num = Math.floor((num - m) / 26);
  }
  return s;
}

function writeSheet(workbook, sheetName, headers, rows) {
  const sheet = workbook.worksheets.add(sheetName);
  const body = rows.length
    ? rows.map((row) => headers.map((header) => valueForCell(row[header])))
    : [headers.map(() => "")];
  const matrix = [headers, ...body];
  sheet.getRangeByIndexes(0, 0, matrix.length, headers.length).values = matrix;

  const used = sheet.getRangeByIndexes(0, 0, matrix.length, headers.length);
  used.format.font = { fontSize: 11, typeface: "Calibri" };
  used.format.autofitRows();

  sheet.getRangeByIndexes(0, 0, 1, headers.length).format.font = { fontSize: 11, typeface: "Calibri" };

  if (sheetName === "1_认缴流量") {
    sheet.getRange("A:A").format.columnWidth = 10;
    sheet.getRange("B:B").format.columnWidth = 14;
    sheet.getRange("C:C").format.columnWidth = 24;
    sheet.getRange("D:F").format.columnWidth = 16;
    sheet.getRange("G:G").format.columnWidth = 90;
    sheet.getRange(`D2:F${matrix.length}`).format.numberFormat = "#,##0.0000";
  } else if (sheetName === "2_股权结构存量") {
    sheet.getRange("A:A").format.columnWidth = 10;
    sheet.getRange("B:C").format.columnWidth = 24;
    sheet.getRange("D:E").format.columnWidth = 18;
    sheet.getRange("F:F").format.columnWidth = 28;
    sheet.getRange("G:I").format.columnWidth = 16;
    sheet.getRange("J:J").format.columnWidth = 70;
    sheet.getRange(`D2:I${matrix.length}`).format.numberFormat = "#,##0.0000";
  } else {
    sheet.getRange("A:D").format.columnWidth = 16;
    sheet.getRange("E:E").format.columnWidth = 34;
    sheet.getRange("F:K").format.columnWidth = 18;
    sheet.getRange("L:L").format.columnWidth = 12;
    sheet.getRange("M:M").format.columnWidth = 80;
    sheet.getRange(`F2:K${matrix.length}`).format.numberFormat = "#,##0.0000";
  }

  return sheet;
}

await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const payload = JSON.parse(await fs.readFile(payloadPath, "utf8"));
const summary = [];
for (const company of payload.companies) {
  const workbook = Workbook.create();
  for (const [sheetName, sheetPayload] of Object.entries(company.sheets)) {
    writeSheet(workbook, sheetName, sheetPayload.headers, sheetPayload.rows);
  }

  for (const sheetName of Object.keys(company.sheets)) {
    const preview = await workbook.render({
      sheetName,
      range: sheetName === "3_schema_cross_check" ? "A1:M18" : sheetName === "2_股权结构存量" ? "A1:J18" : "A1:G18",
      scale: 1,
      format: "png",
    });
    await fs.writeFile(
      `${previewDir}/${company.stock_code}_${sheetName}.png`,
      new Uint8Array(await preview.arrayBuffer()),
    );
  }

  const output = await SpreadsheetFile.exportXlsx(workbook);
  const outputPath = `${outputDir}/${company.output_name}`;
  await output.save(outputPath);
  summary.push({ stock_code: company.stock_code, company_short: company.company_short, output: outputPath });
}

await fs.writeFile(`${outputDir}/生成清单.json`, JSON.stringify(summary, null, 2), "utf8");
console.log(`Generated ${summary.length} reference-style workbooks in ${outputDir}`);
process.exit(0);
