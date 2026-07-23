import fs from "node:fs/promises";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { FileBlob, SpreadsheetFile } = require("@oai/artifact-tool");

const file = "C:/Users/29818/Documents/xwechat_files/wxid_mdm501526cx122_1a20/msg/file/2026-07/301563_云汉芯城_三表抽取.xlsx";
const sheets = ["1_认缴流量", "2_股权结构存量", "3_schema_cross_check"];
const blob = await FileBlob.load(file);
const workbook = await SpreadsheetFile.importXlsx(blob);
const out = [];
for (const sheetName of sheets) {
  const inspection = await workbook.inspect({
    kind: "region,table",
    sheetId: sheetName,
    range: "A1:M20",
    maxChars: 12000,
    tableMaxRows: 12,
    tableMaxCols: 14,
    tableMaxCellChars: 120,
  });
  out.push(`## ${sheetName}\n${inspection.ndjson ?? String(inspection)}\n`);
}
await fs.writeFile("tmp_workbook/reference_style/301563_targeted_sheets.ndjson", out.join("\n"), "utf8");
console.log("targeted sheet inspection done");
process.exit(0);
