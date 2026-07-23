import fs from "node:fs/promises";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { SpreadsheetFile, Workbook } = require("@oai/artifact-tool");

const root = process.cwd();
const inputPath = `${root}/tmp_workbook/workbook_data.json`;
const outputDir = `${root}/final`;
const previewDir = `${root}/tmp_workbook`;

function parseNum(value) {
  if (value === null || value === undefined || value === "") return null;
  const cleaned = String(value).replace(/,/g, "").replace(/%/g, "").trim();
  const number = Number(cleaned);
  return Number.isFinite(number) ? number : null;
}

function shouldBeNumber(header) {
  return /(amount|shares|price|ratio|percent|count|records|points|金额|数量|股份|比例|价格|价|记录|时点|合计|均价)/i.test(header);
}

function cellValue(header, value) {
  if (value === null || value === undefined || value === "") return "";
  if (/code|record_id|source|page|file|股票代码|记录|页码|文件/i.test(header)) return String(value);
  if (shouldBeNumber(header)) {
    const num = parseNum(value);
    if (num !== null) return num;
  }
  return String(value);
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

function tableRange(rowCount, colCount) {
  return `A1:${colLetter(colCount)}${Math.max(rowCount, 1)}`;
}

function addRecordsSheet(workbook, name, records, tableName) {
  const sheet = workbook.worksheets.add(name);
  sheet.showGridLines = false;

  const headers = records.length ? Object.keys(records[0]) : ["说明"];
  const body = records.length
    ? records.map((row) => headers.map((header) => cellValue(header, row[header])))
    : [["无记录"]];
  const matrix = [headers, ...body];
  const range = sheet.getRangeByIndexes(0, 0, matrix.length, headers.length);
  range.values = matrix;
  sheet.getRangeByIndexes(0, 0, 1, headers.length).format = {
    fill: "#1F4E79",
    font: { bold: true, color: "#FFFFFF" },
  };
  range.format.borders = { preset: "all", style: "thin", color: "#D9E2F3" };
  range.format.wrapText = true;
  range.format.autofitColumns();
  range.format.autofitRows();
  sheet.freezePanes.freezeRows(1);
  if (records.length) {
    const table = sheet.tables.add(tableRange(matrix.length, headers.length), true, tableName);
    table.style = "TableStyleMedium2";
  }
  return sheet;
}

function aggregateSummary(data) {
  const manifest = data.summary || [];
  const subs = data.subscription_final || [];
  const transfers = data.transfer_final || [];
  const snaps = data.equity_snapshot_final || [];

  return manifest.map((company) => {
    const code = company.stock_code;
    const companySubs = subs.filter((r) => r.stock_code === code);
    const companyTransfers = transfers.filter((r) => r.stock_code === code);
    const companySnaps = snaps.filter((r) => r.stock_code === code);
    const amount = companySubs.reduce((sum, r) => sum + (parseNum(r.subscription_amount_wan) || 0), 0);
    const prices = companySubs
      .map((r) => parseNum(r.subscription_price_yuan) ?? parseNum(r.computed_price_yuan))
      .filter((v) => v !== null && v >= 0.1 && v <= 500);
    const avgPrice = prices.length ? prices.reduce((a, b) => a + b, 0) / prices.length : "";
    const snapshotPoints = new Set(companySnaps.map((r) => r.time_point).filter(Boolean)).size;
    return {
      股票代码: code,
      公司简称: company.company_short,
      板块: company.board,
      输入状态: company.input_status,
      认缴记录数: companySubs.length,
      确认转让记录数: companyTransfers.length,
      股权快照时点: snapshotPoints,
      认缴金额合计_万元: Number(amount.toFixed(2)),
      平均入股价_元每股: avgPrice === "" ? "" : Number(avgPrice.toFixed(2)),
    };
  });
}

const data = JSON.parse(await fs.readFile(inputPath, "utf8"));
await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const workbook = Workbook.create();
addRecordsSheet(workbook, "Summary", aggregateSummary(data), "SummaryTable");
addRecordsSheet(workbook, "认缴增资Final", data.subscription_final || [], "SubscriptionFinalTable");
addRecordsSheet(workbook, "转让Final", data.transfer_final || [], "TransferFinalTable");
addRecordsSheet(workbook, "股权快照Final", data.equity_snapshot_final || [], "SnapshotFinalTable");
addRecordsSheet(workbook, "CrossCheck", data.cross_check || [], "CrossCheckTable");
addRecordsSheet(workbook, "AutoVsGold", data.auto_vs_gold || [], "AutoVsGoldTable");
addRecordsSheet(workbook, "组内互查", data.review || [], "ReviewTable");

const inspect = await workbook.inspect({
  kind: "workbook,sheet,table",
  maxChars: 6000,
  tableMaxRows: 4,
  tableMaxCols: 8,
});
await fs.writeFile(`${previewDir}/workbook_inspect.ndjson`, inspect.ndjson ?? String(inspect), "utf8");

const preview = await workbook.render({ sheetName: "Summary", autoCrop: "all", scale: 1, format: "png" });
await fs.writeFile(`${previewDir}/summary_preview.png`, new Uint8Array(await preview.arrayBuffer()));

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(`${outputDir}/week6_final_tables.xlsx`);
console.log(`Workbook written: ${outputDir}/week6_final_tables.xlsx`);
process.exit(0);
