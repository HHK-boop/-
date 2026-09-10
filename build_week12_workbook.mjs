import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(path.join(path.dirname(fileURLToPath(import.meta.url)), ".."));
const payloadPath = path.join(root, "outputs", "week12_workbook_data.json");
const outputPath = path.join(root, "outputs", "week12_expansion_workbook.xlsx");
const previewDir = path.join(root, "outputs", "workbook_preview");

const payload = JSON.parse(await fs.readFile(payloadPath, "utf8"));
const tables = payload.tables || {};
const summaryValues = payload.summary || {};

const labels = {
  metric: "指标",
  value: "数值",
  interpretation: "解释",
  source_id: "来源ID",
  source_name: "数据来源",
  source_type: "来源类型",
  local_path: "本地路径",
  records_available: "可用记录数",
  usable_records: "可处理记录数",
  fields_provided: "提供字段",
  week12_usage: "第十二周用途",
  source_limitation: "来源局限",
  company_key: "公司键",
  source_group: "来源组",
  sample_id: "样本ID",
  stock_code: "股票代码",
  company_name: "公司全称",
  company_short: "公司简称",
  exchange: "交易所",
  board: "板块",
  listing_date: "上市日期",
  ipo_year: "IPO年份",
  prospectus_date: "招股书/公告日期",
  source_platform: "来源平台",
  source_page_url: "公告页URL",
  prospectus_url: "PDF URL",
  local_pdf_path: "本地PDF路径",
  local_text_path: "本地文本路径",
  source_status: "来源状态",
  source_level: "来源等级",
  page_count: "页码数",
  file_size_mb: "文件大小MB",
  keyword_hit_count: "关键词命中数",
  keyword_hit_summary: "关键词摘要",
  week12_role: "本周角色",
  recommended_action: "建议动作",
  queue_id: "队列ID",
  priority: "优先级",
  source_url: "来源URL",
  week12_action: "第十二周动作",
  expected_output: "预期产出",
  missing_policy: "缺失处理原则",
  universe_company_count: "公司库数量",
  week12_queue_count: "队列数量",
  with_url_count: "含URL数量",
  with_local_pdf_count: "含本地PDF数量",
  with_local_text_count: "含本地文本数量",
  note: "说明",
  url_coverage_count: "URL覆盖数",
  local_pdf_count: "本地PDF数",
  local_text_count: "本地文本数",
  week12_position: "本周定位",
  field_group: "字段组",
  field_name: "字段名",
  primary_source: "主要来源",
  source_evidence: "证据字段",
  auto_method: "自动处理方法",
  manual_check: "人工核验",
  missing_rule: "缺失规则",
  day: "日期",
  focus: "重点",
  action: "操作",
  expected_output: "预期产出",
  acceptance: "验收标准",
  step_no: "步骤",
  stage: "阶段",
  input: "输入",
  method: "方法",
  output: "输出",
  risk_control: "风险控制",
  gate_id: "门槛ID",
  gate: "质量门槛",
  rule: "规则",
  failure_action: "失败处理",
  table_name: "表名",
  row_count: "行数",
  source_csv: "来源CSV",
  database_schema: "数据库Schema",
  load_status: "导入状态",
  use_case: "用途",
  item: "项目",
  status: "状态",
  evidence: "证据",
  check_item: "检查项",
  detail: "说明",
};

const summaryLabels = {
  run_date: "计划日期",
  generated_at: "生成时间",
  source_groups: "数据来源组数",
  source_inventory_count: "来源台账记录数",
  universe_company_count: "扩样公司库数量",
  processing_queue_count: "本周处理队列数量",
  bse_queue_count: "北交所队列数量",
  star_queue_count: "科创板队列数量",
  local_pdf_universe_count: "含本地PDF公司数",
  local_text_universe_count: "含页码化文本公司数",
};

function colName(n) {
  let s = "";
  while (n > 0) {
    const r = (n - 1) % 26;
    s = String.fromCharCode(65 + r) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

function normalize(value, header = "") {
  if (value === undefined || value === null || Number.isNaN(value)) return null;
  if (value === "") return null;
  if (header === "stock_code") return String(value).padStart(6, "0");
  if (
    typeof value === "string" &&
    /^-?\d+(\.\d+)?$/.test(value.trim()) &&
    !/^0\d+/.test(value.trim()) &&
    header !== "stock_code"
  ) {
    return Number(value);
  }
  return value;
}

function matrix(records, headers) {
  return [
    headers.map((h) => labels[h] || h),
    ...records.map((row) => headers.map((h) => normalize(row[h], h))),
  ];
}

function styleTable(sheet, rows, cols) {
  const end = `${colName(cols)}${Math.max(rows, 1)}`;
  sheet.getRange(`A1:${end}`).format = {
    font: { name: "Microsoft YaHei", size: 10 },
    wrapText: true,
    verticalAlignment: "center",
    borders: {
      insideHorizontal: { style: "thin", color: "#E5E7EB" },
      insideVertical: { style: "thin", color: "#EDF2F7" },
      bottom: { style: "thin", color: "#CBD5E1" },
    },
  };
  sheet.getRange(`A1:${colName(cols)}1`).format = {
    fill: "#17365D",
    font: { name: "Microsoft YaHei", bold: true, color: "#FFFFFF", size: 10 },
    wrapText: true,
  };
  sheet.freezePanes.freezeRows(1);
  sheet.getRange("1:1").format.rowHeight = 28;
  if (rows > 1) sheet.getRange(`2:${rows}`).format.rowHeight = 42;
}

function writeTable(workbook, sheetName, records, headers, widths = {}) {
  const sheet = workbook.worksheets.add(sheetName);
  sheet.showGridLines = false;
  const data = matrix(records || [], headers);
  const rows = data.length;
  const cols = headers.length;
  const end = `${colName(cols)}${rows}`;
  sheet.getRange(`A1:${end}`).values = data;
  styleTable(sheet, rows, cols);
  for (let i = 1; i <= cols; i += 1) {
    const letter = colName(i);
    const header = headers[i - 1];
    sheet.getRange(`${letter}:${letter}`).format.columnWidth = widths[header] || 17;
    if (header === "stock_code") sheet.getRange(`${letter}:${letter}`).format.numberFormat = "@";
    if (
      header.includes("count") ||
      header.includes("rows") ||
      header.includes("page") ||
      header.includes("size") ||
      header === "value" ||
      header === "row_count" ||
      header === "records_available" ||
      header === "usable_records"
    ) {
      sheet.getRange(`${letter}2:${letter}${rows}`).format.numberFormat = "0";
    }
  }
  return sheet;
}

async function renderPreview(workbook, sheetName) {
  try {
    const blob = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
    await fs.writeFile(path.join(previewDir, `${sheetName}.png`), new Uint8Array(await blob.arrayBuffer()));
  } catch (error) {
    console.warn(`preview skipped for ${sheetName}: ${error.message}`);
  }
}

const workbook = Workbook.create();

const summary = workbook.worksheets.add("总览");
summary.showGridLines = false;
summary.getRange("A1:H1").merge();
summary.getRange("A1").values = [["霍泓锟第十二周计划总览"]];
summary.getRange("A1").format = {
  fill: "#17365D",
  font: { name: "Microsoft YaHei", bold: true, color: "#FFFFFF", size: 16 },
};
summary.getRange("1:1").format.rowHeight = 30;
summary.getRange("A2:H2").merge();
summary.getRange("A2").values = [["主题：表明数据来源，并将前期PDF/Markdown抽取流程推广到更多公司"]];
summary.getRange("A2").format = { font: { name: "Microsoft YaHei", color: "#4B5563" } };

const summaryRows = Object.entries(summaryValues).map(([key, value]) => ({
  metric: summaryLabels[key] || key,
  value,
  interpretation:
    key === "universe_company_count"
      ? "去重后的可扩展公司池，不等同于全部已完成人工Gold。"
      : key === "processing_queue_count"
        ? "本周优先推进的P0/P1/P2队列。"
        : key === "local_pdf_universe_count"
          ? "可直接从PDF转Markdown的公司数量。"
          : key === "local_text_universe_count"
            ? "可直接进行章节定位的页码化文本数量。"
            : "由代码自动生成。",
}));

summary.getRange("A4:C4").values = [["指标", "数值", "解释"]];
summary.getRange(`A5:C${4 + summaryRows.length}`).values = summaryRows.map((row) => [
  row.metric,
  normalize(row.value),
  row.interpretation,
]);
summary.getRange(`A4:C${4 + summaryRows.length}`).format = {
  font: { name: "Microsoft YaHei", size: 10 },
  wrapText: true,
  borders: { preset: "all", style: "thin", color: "#B7C9D6" },
};
summary.getRange("A4:C4").format = {
  fill: "#D9EAF7",
  font: { name: "Microsoft YaHei", bold: true, color: "#17365D" },
};
summary.getRange("A:A").format.columnWidth = 28;
summary.getRange("B:B").format.columnWidth = 22;
summary.getRange("C:C").format.columnWidth = 72;

const weeklyPlan = (tables.week12_weekly_plan || []).slice(0, 5);
summary.getRange("E4:H4").values = [["日期", "重点", "操作", "验收标准"]];
summary.getRange(`E5:H${4 + weeklyPlan.length}`).values = weeklyPlan.map((row) => [
  row.day,
  row.focus,
  row.action,
  row.acceptance,
]);
summary.getRange(`E4:H${4 + weeklyPlan.length}`).format = {
  font: { name: "Microsoft YaHei", size: 10 },
  wrapText: true,
  borders: { preset: "all", style: "thin", color: "#B7C9D6" },
};
summary.getRange("E4:H4").format = {
  fill: "#D9EAF7",
  font: { name: "Microsoft YaHei", bold: true, color: "#17365D" },
};
summary.getRange("E:E").format.columnWidth = 25;
summary.getRange("F:F").format.columnWidth = 22;
summary.getRange("G:G").format.columnWidth = 72;
summary.getRange("H:H").format.columnWidth = 54;
summary.getRange("5:12").format.rowHeight = 58;
summary.freezePanes.freezeRows(4);

writeTable(
  workbook,
  "数据来源台账",
  tables.week12_source_catalog,
  [
    "source_id",
    "source_name",
    "source_type",
    "local_path",
    "records_available",
    "usable_records",
    "fields_provided",
    "week12_usage",
    "source_limitation",
  ],
  { source_name: 42, local_path: 76, fields_provided: 58, week12_usage: 58, source_limitation: 56 },
);

writeTable(
  workbook,
  "来源明细",
  tables.week12_source_summary,
  [
    "source_group",
    "universe_company_count",
    "week12_queue_count",
    "with_url_count",
    "with_local_pdf_count",
    "with_local_text_count",
    "note",
  ],
  { source_group: 34, note: 58 },
);

writeTable(
  workbook,
  "扩样公司库",
  tables.week12_expanded_company_universe,
  [
    "source_group",
    "sample_id",
    "stock_code",
    "company_short",
    "company_name",
    "board",
    "listing_date",
    "prospectus_date",
    "source_platform",
    "source_page_url",
    "prospectus_url",
    "local_pdf_path",
    "local_text_path",
    "source_status",
    "source_level",
    "page_count",
    "file_size_mb",
    "week12_role",
    "recommended_action",
  ],
  {
    company_name: 42,
    source_platform: 36,
    source_page_url: 58,
    prospectus_url: 74,
    local_pdf_path: 78,
    local_text_path: 74,
    recommended_action: 62,
  },
);

writeTable(
  workbook,
  "本周处理队列",
  tables.week12_processing_queue,
  [
    "queue_id",
    "priority",
    "stock_code",
    "company_short",
    "company_name",
    "board",
    "source_group",
    "source_url",
    "local_pdf_path",
    "local_text_path",
    "page_count",
    "file_size_mb",
    "keyword_hit_summary",
    "week12_action",
    "expected_output",
    "missing_policy",
  ],
  {
    priority: 26,
    company_name: 42,
    source_url: 74,
    local_pdf_path: 78,
    local_text_path: 74,
    keyword_hit_summary: 52,
    week12_action: 62,
    expected_output: 52,
    missing_policy: 50,
  },
);

writeTable(
  workbook,
  "字段来源矩阵",
  tables.week12_field_source_matrix,
  ["field_group", "field_name", "primary_source", "source_evidence", "auto_method", "manual_check", "missing_rule"],
  {
    field_group: 20,
    field_name: 28,
    primary_source: 42,
    source_evidence: 44,
    auto_method: 46,
    manual_check: 44,
    missing_rule: 42,
  },
);

writeTable(
  workbook,
  "第十二周计划",
  tables.week12_weekly_plan,
  ["day", "focus", "action", "expected_output", "acceptance"],
  { day: 26, focus: 24, action: 78, expected_output: 54, acceptance: 58 },
);

writeTable(
  workbook,
  "推广流程",
  tables.week12_scaling_protocol,
  ["step_no", "stage", "input", "method", "output", "risk_control"],
  { stage: 22, input: 44, method: 58, output: 34, risk_control: 56 },
);

writeTable(
  workbook,
  "板块覆盖",
  tables.week12_board_coverage_summary,
  [
    "board",
    "universe_company_count",
    "week12_queue_count",
    "url_coverage_count",
    "local_pdf_count",
    "local_text_count",
    "week12_position",
  ],
  { week12_position: 34 },
);

writeTable(
  workbook,
  "PostgreSQL计划",
  tables.week12_database_load_plan,
  ["table_name", "row_count", "source_csv", "database_schema", "load_status", "use_case"],
  { table_name: 42, source_csv: 56, use_case: 46 },
);

writeTable(
  workbook,
  "PG披露结果",
  tables.postgresql_week12_disclosure && tables.postgresql_week12_disclosure.length
    ? tables.postgresql_week12_disclosure
    : [{ item: "状态", value: "未生成", source_note: "先运行database/run_postgres_temp_week12.ps1" }],
  ["item", "value", "source_note"],
  { item: 34, value: 32, source_note: 72 },
);

writeTable(
  workbook,
  "PG表行数",
  tables.postgresql_week12_table_counts || [],
  ["table_name", "row_count"],
  { table_name: 54, row_count: 16 },
);

writeTable(
  workbook,
  "质量门槛",
  tables.week12_quality_gates,
  ["gate_id", "gate", "rule", "failure_action"],
  { gate: 28, rule: 82, failure_action: 50 },
);

writeTable(
  workbook,
  "验证清单",
  tables.week12_validation_summary,
  ["check_item", "status", "detail"],
  { check_item: 34, detail: 76 },
);

writeTable(
  workbook,
  "提交清单",
  tables.week12_submission_checklist,
  ["item", "status", "evidence"],
  { item: 34, evidence: 84 },
);

await fs.mkdir(path.dirname(outputPath), { recursive: true });
const inspect = await workbook.inspect({
  kind: "workbook,sheet,table,drawing,formula",
  maxChars: 14000,
  tableMaxRows: 8,
  tableMaxCols: 8,
});
await fs.writeFile(`${outputPath}.inspect.ndjson`, inspect.ndjson);

if (process.argv.includes("--render")) {
  await fs.mkdir(previewDir, { recursive: true });
  for (const sheetName of ["总览", "数据来源台账", "本周处理队列", "字段来源矩阵", "PG披露结果", "验证清单"]) {
    await renderPreview(workbook, sheetName);
  }
}

const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);
console.log(`saved ${outputPath}`);
