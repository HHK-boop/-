import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(path.join(path.dirname(fileURLToPath(import.meta.url)), ".."));
const localModules = path.join(root, "node_modules");
try {
  await fs.stat(localModules);
} catch {
  console.error(
    "Missing local node_modules. In Codex, create a junction to the bundled runtime before running this script. See README.md.",
  );
  process.exit(2);
}

const payloadPath = path.join(root, "outputs", "week8_workbook_data.json");
const outputPath = path.join(root, "outputs", "week8_summary_workbook.xlsx");
const previewDir = path.join(root, "outputs", "workbook_preview");
const payload = JSON.parse(await fs.readFile(payloadPath, "utf8"));

function colName(n) {
  let s = "";
  while (n > 0) {
    const r = (n - 1) % 26;
    s = String.fromCharCode(65 + r) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

function normalize(value) {
  if (value === undefined || value === null || Number.isNaN(value)) return null;
  return value;
}

function matrixFromRecords(records, headers) {
  return [headers, ...records.map((row) => headers.map((h) => normalize(row[h])))];
}

function writeTable(workbook, sheetName, records, headers, widths = {}) {
  const sheet = workbook.worksheets.add(sheetName);
  sheet.showGridLines = false;
  const matrix = matrixFromRecords(records, headers);
  const rowCount = matrix.length;
  const colCount = headers.length;
  const end = `${colName(colCount)}${rowCount}`;
  sheet.getRange(`A1:${end}`).values = matrix;
  sheet.getRange(`A1:${colName(colCount)}1`).format = {
    fill: "#1F4D78",
    font: { bold: true, color: "#FFFFFF" },
    borders: { preset: "all", style: "thin", color: "#D9E2F3" },
  };
  sheet.getRange(`A1:${end}`).format.borders = { preset: "inside", style: "thin", color: "#E5E7EB" };
  sheet.getRange(`A1:${end}`).format.wrapText = true;
  sheet.freezePanes.freezeRows(1);
  for (let c = 1; c <= colCount; c += 1) {
    const letter = colName(c);
    const header = headers[c - 1];
    sheet.getRange(`${letter}:${letter}`).format.columnWidth = widths[header] || 16;
  }
  return sheet;
}

const workbook = Workbook.create();

const summary = workbook.worksheets.add("总览");
summary.showGridLines = false;
summary.getRange("A1:H1").merge();
summary.getRange("A1").values = [["霍泓锟第八周任务总览"]];
summary.getRange("A1").format = {
  fill: "#17365D",
  font: { bold: true, color: "#FFFFFF", size: 16 },
};
summary.getRange("A2:H2").merge();
summary.getRange("A2").values = [["PE/VC招股书三表质量审计、数据库化准备与研究变量草案"]];
summary.getRange("A2").format = { font: { color: "#4B5563" } };
summary.getRange("A4:C4").values = [["指标", "数值", "说明"]];
summary.getRange("A5:C11").values = [
  ["样本公司", payload.summary.company_count, "统一8家公司样本"],
  ["认缴/增资记录", payload.summary.subscription_records, "来自第七周Final表"],
  ["股权快照记录", payload.summary.snapshot_records, "来自第七周Final表"],
  ["股权转让记录", payload.summary.transfer_records, "仅保留可回溯证据事件"],
  ["广义PE/VC相关记录", payload.summary.broad_pevc_records, "VC、PE、政府基金、产业资本/CVC等"],
  ["P1人工复核项", payload.summary.p1_review_items, "需要回PDF核验的优先问题"],
  ["运行时间", payload.summary.run_time, "由主流程自动生成"],
];
summary.getRange("A4:C4").format = {
  fill: "#D9EAF7",
  font: { bold: true, color: "#17365D" },
};
summary.getRange("A4:C11").format.borders = { preset: "all", style: "thin", color: "#B7C9D6" };
summary.getRange("A:A").format.columnWidth = 24;
summary.getRange("B:B").format.columnWidth = 18;
summary.getRange("C:C").format.columnWidth = 52;

summary.getRange("E4:F4").values = [["投资主体类型", "记录数"]];
summary.getRange(`E5:F${4 + payload.investor_type_stats.length}`).values =
  payload.investor_type_stats.map((row) => [row.investor_type_final, row.record_count]);
summary.getRange("E4:F4").format = {
  fill: "#D9EAF7",
  font: { bold: true, color: "#17365D" },
};
const chart = summary.charts.add("bar", summary.getRange(`E4:F${4 + payload.investor_type_stats.length}`));
chart.title = "investor_type记录分布";
chart.hasLegend = false;
chart.setPosition("H4", "N19");
summary.freezePanes.freezeRows(4);

writeTable(
  workbook,
  "任务状态",
  payload.task_status,
  ["week8_task", "status", "evidence_file", "remaining_work"],
  { week8_task: 30, status: 18, evidence_file: 42, remaining_work: 50 },
);

writeTable(
  workbook,
  "公司概况",
  payload.company_summary,
  [
    "stock_code",
    "company_short",
    "market",
    "subscription_records",
    "snapshot_records",
    "transfer_records",
    "total_records",
    "broad_pevc_records",
    "evidence_coverage",
  ],
  { stock_code: 12, company_short: 16, market: 12, evidence_coverage: 16 },
);

writeTable(
  workbook,
  "质量指标",
  payload.quality_metrics,
  [
    "table_name",
    "total_records",
    "pdf_page_coverage",
    "evidence_coverage",
    "investor_type_coverage",
    "review_queue_items",
    "quality_note",
  ],
  { table_name: 18, quality_note: 48 },
);

writeTable(
  workbook,
  "分类统计",
  payload.investor_type_stats,
  ["investor_type_final", "record_count", "share"],
  { investor_type_final: 28, record_count: 14, share: 12 },
);

writeTable(
  workbook,
  "缺失字段Top",
  payload.missing_summary_top,
  ["table_name", "field", "records", "missing_count", "missing_rate", "week8_principle"],
  { table_name: 18, field: 32, week8_principle: 44 },
);

writeTable(
  workbook,
  "板块统计",
  payload.board_stats,
  [
    "market",
    "company_count",
    "subscription_records",
    "snapshot_records",
    "transfer_records",
    "broad_pevc_records",
    "broad_pevc_record_share",
  ],
  { market: 14, broad_pevc_record_share: 24 },
);

writeTable(
  workbook,
  "研究变量草案",
  payload.research_variables,
  [
    "stock_code",
    "company_short",
    "market",
    "has_vc_or_pe",
    "vc_record_count",
    "pe_record_count",
    "broad_pevc_record_share",
    "natural_person_record_share",
    "distinct_investor_type_count",
    "transfer_event_count",
    "p1_review_item_count",
    "research_use_note",
  ],
  { company_short: 16, broad_pevc_record_share: 22, natural_person_record_share: 24, research_use_note: 48 },
);

writeTable(
  workbook,
  "人工复核队列",
  payload.review_queue,
  ["queue_id", "stock_code", "company_short", "source", "issue_type", "status", "detail", "suggested_action"],
  { queue_id: 16, company_short: 22, source: 24, issue_type: 26, status: 16, detail: 58, suggested_action: 52 },
);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
  maxChars: 1200,
});
console.log(errors.ndjson);

await fs.mkdir(previewDir, { recursive: true });
for (const sheetName of [
  "总览",
  "任务状态",
  "公司概况",
  "质量指标",
  "分类统计",
  "缺失字段Top",
  "板块统计",
  "研究变量草案",
  "人工复核队列",
]) {
  const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(path.join(previewDir, `${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`saved ${outputPath}`);
