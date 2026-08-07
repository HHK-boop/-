import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(path.join(path.dirname(fileURLToPath(import.meta.url)), ".."));
const dataPath = path.join(root, "tables", "week7_workbook_data.json");
const outputPath = path.join(root, "tables", "week7_summary_workbook.xlsx");
const previewDir = path.join(root, "tables", "preview");

const payload = JSON.parse(await fs.readFile(dataPath, "utf8"));

function colName(n) {
  let s = "";
  while (n > 0) {
    const r = (n - 1) % 26;
    s = String.fromCharCode(65 + r) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

function normalizeValue(value) {
  if (value === null || value === undefined) return null;
  if (typeof value === "number" && Number.isNaN(value)) return null;
  return value;
}

function matrixFromRecords(records, preferredHeaders = null) {
  const headers = preferredHeaders || Array.from(
    records.reduce((set, row) => {
      Object.keys(row).forEach((k) => set.add(k));
      return set;
    }, new Set()),
  );
  const rows = records.map((row) => headers.map((h) => normalizeValue(row[h])));
  return [headers, ...rows];
}

function writeRecords(workbook, sheetName, records, headers = null, widthMap = {}) {
  const sheet = workbook.worksheets.add(sheetName);
  sheet.showGridLines = false;
  const matrix = matrixFromRecords(records, headers);
  const rowCount = matrix.length;
  const colCount = matrix[0].length;
  const end = `${colName(colCount)}${rowCount}`;
  const range = sheet.getRange(`A1:${end}`);
  range.values = matrix;

  const header = sheet.getRange(`A1:${colName(colCount)}1`);
  header.format = {
    fill: "#1F4D78",
    font: { bold: true, color: "#FFFFFF" },
    borders: { preset: "all", style: "thin", color: "#D9E2F3" },
  };
  range.format.borders = { preset: "inside", style: "thin", color: "#E5E7EB" };
  range.format.wrapText = true;
  sheet.freezePanes.freezeRows(1);

  for (let c = 1; c <= colCount; c += 1) {
    const letter = colName(c);
    const headerText = matrix[0][c - 1];
    const width = widthMap[headerText] || 18;
    sheet.getRange(`${letter}:${letter}`).format.columnWidth = width;
  }
  if (rowCount > 1) {
    sheet.getRange(`A2:${colName(colCount)}${rowCount}`).format = {
      font: { color: "#111827" },
    };
  }
  return sheet;
}

const workbook = Workbook.create();

const summary = workbook.worksheets.add("总览");
summary.showGridLines = false;
summary.getRange("A1:G1").merge();
summary.getRange("A1").values = [["第七周任务提交总览"]];
summary.getRange("A1").format = {
  fill: "#1F4D78",
  font: { bold: true, color: "#FFFFFF", size: 16 },
};
summary.getRange("A1:G1").format.rowHeight = 32;
summary.getRange("A2:G2").merge();
summary.getRange("A2").values = [["霍泓锟｜PE/VC招股书三表数据治理、investor_type统一、互查差异与PostgreSQL草案"]];
summary.getRange("A2").format = { font: { color: "#4B5563" } };
summary.getRange("A2:G2").format.rowHeight = 24;

summary.getRange("A4:C4").values = [["指标", "数值", "说明"]];
summary.getRange("A5:C11").values = payload.summary.map((r) => [r.metric, r.value, r.note]);
summary.getRange("A4:C4").format = {
  fill: "#E8EEF5",
  font: { bold: true, color: "#0B2545" },
  borders: { preset: "all", style: "thin", color: "#CBD5E1" },
};
summary.getRange("A4:C11").format.borders = { preset: "all", style: "thin", color: "#CBD5E1" };
summary.getRange("A:A").format.columnWidth = 24;
summary.getRange("B:B").format.columnWidth = 14;
summary.getRange("C:C").format.columnWidth = 48;
summary.freezePanes.freezeRows(4);

const chartDataStart = 14;
summary.getRange(`A${chartDataStart}:B${chartDataStart}`).values = [["investor_type_final", "record_count"]];
summary.getRange(`A${chartDataStart + 1}:B${chartDataStart + payload.investor_type_stats.length}`).values =
  payload.investor_type_stats.map((r) => [r.investor_type_final, r.record_count]);
summary.getRange(`A${chartDataStart}:B${chartDataStart}`).format = {
  fill: "#E8EEF5",
  font: { bold: true, color: "#0B2545" },
};

const chart = summary.charts.add(
  "bar",
  summary.getRange(`A${chartDataStart}:B${chartDataStart + payload.investor_type_stats.length}`),
);
chart.title = "投资主体类型分布";
chart.hasLegend = false;
chart.setPosition("E4", "L20");

writeRecords(
  workbook,
  "公司记录概况",
  payload.company_records,
  ["stock_code", "company_short", "market", "subscription_records", "snapshot_records", "transfer_records"],
  { stock_code: 12, company_short: 16, market: 12 },
);

writeRecords(
  workbook,
  "投资主体统计",
  payload.investor_type_stats,
  ["investor_type_final", "record_count", "share"],
  { investor_type_final: 26, record_count: 14, share: 12 },
);

writeRecords(
  workbook,
  "字段缺失率",
  payload.missing_summary,
  ["table_name", "field", "records", "missing_count", "missing_rate", "week7_principle"],
  { table_name: 18, field: 28, week7_principle: 44 },
);

writeRecords(
  workbook,
  "问题日志",
  payload.issue_log,
  ["issue_id", "stock_code", "company_short", "source", "issue_type", "status", "detail", "week7_action"],
  { issue_id: 14, stock_code: 12, company_short: 14, source: 18, issue_type: 22, status: 12, detail: 34, week7_action: 42 },
);

writeRecords(
  workbook,
  "Auto-vs-Gold",
  payload.auto_vs_gold,
  ["table_name", "metric", "status", "detail"],
  { table_name: 20, metric: 22, status: 12, detail: 58 },
);

writeRecords(
  workbook,
  "分类字典",
  payload.investor_type_dictionary,
  ["investor_type_final", "classification_rule", "boundary_note", "example"],
  { investor_type_final: 22, classification_rule: 48, boundary_note: 46, example: 24 },
);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "formula error scan",
  maxChars: 1000,
});
console.log(errors.ndjson);

await fs.mkdir(previewDir, { recursive: true });
for (const sheetName of ["总览", "公司记录概况", "投资主体统计", "字段缺失率", "问题日志", "Auto-vs-Gold", "分类字典"]) {
  const preview = await workbook.render({
    sheetName,
    autoCrop: "all",
    scale: 1,
    format: "png",
  });
  await fs.writeFile(
    path.join(previewDir, `${sheetName}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`saved ${outputPath}`);
process.exit(0);
