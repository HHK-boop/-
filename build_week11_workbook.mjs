import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(path.join(path.dirname(fileURLToPath(import.meta.url)), ".."));
const payload = JSON.parse(await fs.readFile(path.join(root, "outputs", "week11_workbook_data.json"), "utf8"));
const outputPath = path.join(root, "outputs", "week11_summary_workbook.xlsx");
const previewDir = path.join(root, "outputs", "workbook_preview");

function colName(n) {
  let s = "";
  while (n > 0) {
    const r = (n - 1) % 26;
    s = String.fromCharCode(65 + r) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

const labels = {
  step_id: "步骤编号",
  task: "任务",
  status: "状态",
  evidence: "证据",
  remaining_risk: "剩余风险",
  next_action: "下一步",
  check_item: "检查项",
  result: "结果",
  detail: "说明",
  action: "动作",
  record_id: "记录ID",
  investor_name: "投资主体名称",
  investor_type_final: "主体类型",
  investor_type_basis: "分类依据",
  stock_code: "证券代码",
  company_short: "公司简称",
  market: "板块",
  manual_priority: "人工优先级",
  source_tables: "来源表",
  pdf_pages_observed: "PDF页码",
  amac_record_code: "备案编码",
  gp_name: "GP",
  lp_structure: "LP结构",
  pdf_direct_disclosure: "PDF直接披露",
  needs_amac_check: "需核备案",
  needs_gp_lp_check: "需核GP/LP",
  verification_priority: "核验优先级",
  source_priority: "来源优先级",
  week11_status: "第十一周状态",
  manual_instruction: "人工说明",
  engineering_rule: "工程原则",
  verify_item: "核验字段",
  current_value: "当前值",
  evidence_location: "证据位置",
  manual_rule: "人工规则",
  suggested_action: "建议动作",
  check_result: "核验结果",
  reviewer: "复核人",
  update_target: "更新位置",
  question_id: "问题编号",
  research_question: "研究问题",
  dependent_variable: "被解释变量",
  key_explanatory_variable: "核心解释变量",
  controls: "控制变量",
  sample_scope: "样本范围",
  method: "方法",
  current_limit: "当前限制",
  week11_output: "本周输出",
  variable: "变量名",
  cn_name: "中文名",
  table: "来源表",
  type: "类型",
  definition: "定义",
  derivation: "生成方式",
  plan_id: "计划编号",
  period: "周期",
  scope: "范围",
  target: "目标",
  success_criteria: "验收标准",
  metric: "指标",
  value: "数值",
  interpretation: "解释",
  item: "项目",
  source_note: "来源说明",
  file: "文件",
  rows: "行数",
  role: "作用",
  source: "来源",
  row_count: "行数",
  broad_pevc_record_share: "PE/VC记录占比",
  pevc_strength_index: "PE/VC强度指数",
  top1_ratio_pct: "第一大股东比例",
  hhi: "HHI",
  effective_shareholder_count: "有效股东数",
  analysis_sample_flag: "主分析样本",
  quality_gate: "质量门槛",
};

function normalize(value, header = "") {
  if (value === undefined || value === null || Number.isNaN(value)) return null;
  if (value === "") return null;
  if (header === "stock_code") return String(value).padStart(6, "0");
  if (typeof value === "string" && /^-?\d+(\.\d+)?$/.test(value.trim()) && !/^0\d+/.test(value.trim())) {
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
  if (rows > 1) sheet.getRange(`2:${rows}`).format.rowHeight = 44;
}

function writeTable(workbook, sheetName, records, headers, widths = {}) {
  const sheet = workbook.worksheets.add(sheetName);
  sheet.showGridLines = false;
  const data = matrix(records, headers);
  const rows = data.length;
  const cols = headers.length;
  const end = `${colName(cols)}${rows}`;
  sheet.getRange(`A1:${end}`).values = data;
  styleTable(sheet, rows, cols);
  for (let i = 1; i <= cols; i += 1) {
    const letter = colName(i);
    const header = headers[i - 1];
    sheet.getRange(`${letter}:${letter}`).format.columnWidth = widths[header] || 16;
    if (header === "stock_code") sheet.getRange(`${letter}:${letter}`).format.numberFormat = "@";
    if (
      header.includes("pct") ||
      header.includes("share") ||
      header.includes("rate") ||
      header.includes("hhi") ||
      header.includes("index") ||
      header.includes("count") ||
      header.includes("rows") ||
      header === "value"
    ) {
      sheet.getRange(`${letter}2:${letter}${rows}`).format.numberFormat = "0.000";
    }
  }
  return sheet;
}

const tables = payload.tables;
const workbook = Workbook.create();

const summary = workbook.worksheets.add("总览");
summary.showGridLines = false;
summary.getRange("A1:H1").merge();
summary.getRange("A1").values = [["霍泓锟第十一周任务总览"]];
summary.getRange("A1").format = {
  fill: "#17365D",
  font: { name: "Microsoft YaHei", bold: true, color: "#FFFFFF", size: 16 },
};
summary.getRange("1:1").format.rowHeight = 30;
summary.getRange("A2:H2").merge();
summary.getRange("A2").values = [["数据库长期化迁移准备、基金AMAC/GP/LP深度核验队列与后续研究设计"]];
summary.getRange("A2").format = { font: { name: "Microsoft YaHei", color: "#4B5563" } };

const quality = tables.quality_dashboard || [];
summary.getRange("A4:C4").values = [["指标", "数值", "解释"]];
summary.getRange(`A5:C${4 + quality.length}`).values = quality.map((row) => [
  row.metric,
  normalize(row.value),
  row.interpretation,
]);
summary.getRange(`A4:C${4 + quality.length}`).format = {
  font: { name: "Microsoft YaHei", size: 10 },
  wrapText: true,
  borders: { preset: "all", style: "thin", color: "#B7C9D6" },
};
summary.getRange("A4:C4").format = {
  fill: "#D9EAF7",
  font: { name: "Microsoft YaHei", bold: true, color: "#17365D" },
};
summary.getRange("A:A").format.columnWidth = 26;
summary.getRange("B:B").format.columnWidth = 24;
summary.getRange("C:C").format.columnWidth = 76;
summary.freezePanes.freezeRows(4);

summary.getRange("E4:H4").values = [["任务", "状态", "证据", "下一步"]];
const planRows = (tables.database_migration_plan || []).slice(0, 5);
summary.getRange(`E5:H${4 + planRows.length}`).values = planRows.map((row) => [
  row.task,
  row.status,
  row.evidence,
  row.next_action,
]);
summary.getRange(`E4:H${4 + planRows.length}`).format = {
  font: { name: "Microsoft YaHei", size: 10 },
  wrapText: true,
  borders: { preset: "all", style: "thin", color: "#B7C9D6" },
};
summary.getRange("E4:H4").format = {
  fill: "#D9EAF7",
  font: { name: "Microsoft YaHei", bold: true, color: "#17365D" },
};
summary.getRange("E:E").format.columnWidth = 24;
summary.getRange("F:F").format.columnWidth = 22;
summary.getRange("G:G").format.columnWidth = 70;
summary.getRange("H:H").format.columnWidth = 56;
summary.getRange("5:15").format.rowHeight = 48;

writeTable(
  workbook,
  "数据库迁移",
  tables.database_migration_plan,
  ["step_id", "task", "status", "evidence", "remaining_risk", "next_action"],
  { evidence: 58, remaining_risk: 40, next_action: 44 },
);

writeTable(
  workbook,
  "PG准备状态",
  tables.persistent_db_readiness,
  ["check_item", "result", "detail", "action"],
  { detail: 72, action: 50 },
);

writeTable(
  workbook,
  "PG披露结果",
  tables.postgresql_week11_disclosure && tables.postgresql_week11_disclosure.length
    ? tables.postgresql_week11_disclosure
    : [{ item: "状态", value: "未生成", source_note: "先运行database/run_postgres_temp_week11.ps1" }],
  ["item", "value", "source_note"],
  { item: 28, value: 28, source_note: 72 },
);

writeTable(
  workbook,
  "PG表行数",
  tables.postgresql_week11_table_counts || [],
  ["table_name", "row_count"],
  { table_name: 52, row_count: 14 },
);

writeTable(
  workbook,
  "基金深度队列",
  tables.fund_deep_enrichment_queue,
  [
    "record_id",
    "investor_name",
    "investor_type_final",
    "stock_code",
    "company_short",
    "market",
    "manual_priority",
    "pdf_pages_observed",
    "amac_record_code",
    "gp_name",
    "lp_structure",
    "pdf_direct_disclosure",
    "needs_amac_check",
    "needs_gp_lp_check",
    "verification_priority",
    "week11_status",
    "engineering_rule",
  ],
  {
    investor_name: 48,
    manual_priority: 32,
    pdf_pages_observed: 24,
    engineering_rule: 46,
  },
);

writeTable(
  workbook,
  "人工核验模板",
  tables.manual_verification_template,
  [
    "record_id",
    "stock_code",
    "company_short",
    "investor_name",
    "investor_type_final",
    "verify_item",
    "current_value",
    "evidence_location",
    "manual_rule",
    "suggested_action",
    "check_result",
    "reviewer",
    "update_target",
  ],
  { investor_name: 44, manual_rule: 40, suggested_action: 50, evidence_location: 24 },
);

writeTable(
  workbook,
  "研究设计",
  tables.research_design_matrix,
  [
    "question_id",
    "research_question",
    "dependent_variable",
    "key_explanatory_variable",
    "controls",
    "sample_scope",
    "method",
    "current_limit",
    "week11_output",
  ],
  {
    research_question: 48,
    dependent_variable: 36,
    key_explanatory_variable: 38,
    controls: 42,
    sample_scope: 48,
    current_limit: 48,
  },
);

writeTable(
  workbook,
  "变量字典",
  tables.variable_dictionary,
  ["variable", "cn_name", "table", "type", "definition", "derivation"],
  { variable: 30, table: 38, definition: 48, derivation: 50 },
);

writeTable(
  workbook,
  "样本扩展计划",
  tables.sample_expansion_plan,
  ["plan_id", "period", "scope", "target", "success_criteria", "status"],
  { scope: 30, target: 70, success_criteria: 58 },
);

writeTable(
  workbook,
  "质量仪表盘",
  tables.quality_dashboard,
  ["metric", "value", "interpretation"],
  { metric: 30, interpretation: 76 },
);

writeTable(
  workbook,
  "第十周公司面板",
  tables.week10_company_panel,
  [
    "stock_code",
    "company_short",
    "market",
    "broad_pevc_record_share",
    "pevc_strength_index",
    "top1_ratio_pct",
    "hhi",
    "effective_shareholder_count",
    "analysis_sample_flag",
    "quality_gate",
  ],
  { company_short: 18, quality_gate: 18 },
);

writeTable(
  workbook,
  "提交清单",
  tables.completion_checklist,
  ["item", "status", "evidence"],
  { item: 36, evidence: 72 },
);

writeTable(
  workbook,
  "文件清单",
  tables.manifest,
  ["file", "rows", "role", "source"],
  { file: 56, role: 34, source: 48 },
);

await fs.mkdir(path.dirname(outputPath), { recursive: true });
const inspect = await workbook.inspect({
  kind: "workbook,sheet,table,drawing,formula",
  maxChars: 12000,
  tableMaxRows: 8,
  tableMaxCols: 8,
});
await fs.writeFile(`${outputPath}.inspect.ndjson`, inspect.ndjson);

if (process.argv.includes("--render")) {
  await fs.mkdir(previewDir, { recursive: true });
  for (const sheetName of [
    "总览",
    "数据库迁移",
    "PG披露结果",
    "基金深度队列",
    "人工核验模板",
    "研究设计",
    "质量仪表盘",
    "第十周公司面板",
  ]) {
    const blob = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
    await fs.writeFile(path.join(previewDir, `${sheetName}.png`), new Uint8Array(await blob.arrayBuffer()));
  }
}

const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);
console.log(`saved ${outputPath}`);
