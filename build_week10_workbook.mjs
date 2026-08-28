import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(path.join(path.dirname(fileURLToPath(import.meta.url)), ".."));
const payload = JSON.parse(await fs.readFile(path.join(root, "outputs", "week10_workbook_data.json"), "utf8"));
const outputPath = path.join(root, "outputs", "week10_summary_workbook.xlsx");
const previewDir = path.join(root, "outputs", "workbook_preview");

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let inQuotes = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];
    if (ch === '"') {
      if (inQuotes && next === '"') {
        cell += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (ch === "," && !inQuotes) {
      row.push(cell);
      cell = "";
    } else if ((ch === "\n" || ch === "\r") && !inQuotes) {
      if (ch === "\r" && next === "\n") i += 1;
      row.push(cell);
      if (row.some((v) => v !== "")) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += ch;
    }
  }
  if (cell !== "" || row.length) {
    row.push(cell);
    if (row.some((v) => v !== "")) rows.push(row);
  }
  if (!rows.length) return [];
  const headers = rows[0];
  return rows.slice(1).map((values) => Object.fromEntries(headers.map((h, idx) => [h, values[idx] ?? ""])));
}

async function readCsvMaybe(relativePath) {
  try {
    const text = await fs.readFile(path.join(root, relativePath), "utf8");
    return parseCsv(text.replace(/^\uFEFF/, ""));
  } catch {
    return [];
  }
}

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
  stock_code: "证券代码",
  company_short: "公司简称",
  market: "板块",
  has_vc_or_pe: "是否有VC/PE",
  broad_pevc_record_share: "广义PE/VC记录占比",
  pevc_intensity_level: "PE/VC强度",
  distinct_investor_type_count: "投资主体类型数",
  transfer_event_count: "转让事件数",
  top1_ratio_pct: "第一大股东比例",
  top3_ratio_pct: "前三大股东比例",
  hhi: "HHI",
  effective_shareholder_count: "有效股东数",
  broad_pevc_holder_count: "广义PE/VC股东数",
  broad_pevc_ratio_sum_pct: "广义PE/VC持股比例",
  dispersion_level: "分散度判断",
  pevc_strength_index: "PE/VC进入强度指数",
  pre_ipo_dispersion_index: "上市前分散度指数",
  caution_flag: "谨慎样本",
  analysis_sample_flag: "分析样本",
  quality_gate: "质量门槛",
  investor_name: "投资主体名称",
  investor_type_final: "主体类型",
  is_broad_pevc: "是否广义PE/VC",
  is_fund_like_name: "名称似基金/平台",
  record_count: "记录数",
  company_count: "公司数",
  companies: "涉及公司",
  markets: "涉及板块",
  source_tables: "来源表",
  pdf_pages_observed: "PDF页码",
  manual_priority: "人工优先级",
  amac_record_code: "备案编码",
  gp_name: "GP",
  lp_structure: "LP结构",
  disclosure_status: "披露状态",
  next_action: "下一步动作",
  week10_principle: "工程原则",
  ratio_timepoints: "快照时点数",
  usable_ratio_timepoints: "可用时点",
  invalid_ratio_timepoints: "不可用时点",
  abnormal_ratio_timepoints: "异常时点",
  blank_ratio_timepoints: "空值时点",
  week8_p1_count: "第八周P1",
  week9_closed_p1_count: "第九周已闭环",
  quality_note: "质量说明",
  table_name: "表名",
  field_name: "字段名",
  observed_count: "非空数",
  missing_count: "缺失数",
  missing_rate: "缺失率",
  week10_action: "第十周处理",
  variable: "变量",
  variable_label: "变量含义",
  n: "样本量",
  mean: "均值",
  median: "中位数",
  std: "标准差",
  min: "最小值",
  max: "最大值",
  interpretation: "解释",
  avg_pevc_strength_index: "平均PE/VC强度",
  avg_broad_pevc_record_share: "平均PE/VC占比",
  avg_top1_ratio_pct: "平均第一大股东比例",
  avg_hhi: "平均HHI",
  avg_effective_shareholder_count: "平均有效股东数",
  caution_company_count: "谨慎公司数",
  week10_interpretation: "口径说明",
  var_left: "变量1",
  var_right: "变量2",
  pearson_corr: "相关系数",
  note: "说明",
  model_id: "模型编号",
  sample_scope: "样本范围",
  dependent_variable: "被解释变量",
  independent_variable: "解释变量",
  intercept: "截距",
  coef_x: "系数",
  std_error_x: "标准误",
  t_stat_x: "t值",
  r_squared: "R方",
  model_note: "模型说明",
  question_id: "问题编号",
  research_question: "研究问题",
  current_evidence: "当前证据",
  current_judgement: "当前判断",
  next_data_need: "下一步数据需求",
  check_item: "检查项",
  status: "状态",
  result: "结果",
  check_name: "检查项",
  detail: "说明",
  item: "披露项目",
  value: "披露值",
  source_note: "来源说明",
  table_name: "表名",
  row_count: "行数",
  source_record_count: "来源记录数",
  company_mentions: "公司出现次数",
  broad_pevc_profiles: "广义PE/VC主体数",
  fund_like_profiles: "基金/平台名称主体数",
  fund_queue_rows: "基金队列行数",
  amac_code_filled: "备案编码已填",
  gp_filled: "GP已填",
  lp_structure_filled: "LP结构已填",
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

function displayStatus(value) {
  const map = {
    READY_NEED_PASSWORD: "需密码后导入",
    READY_WITH_PASSWORD: "可执行导入",
  };
  return map[value] || value;
}

const pgDisclosure = await readCsvMaybe("database/postgresql_disclosure_summary_week10.csv");
const pgTableCounts = await readCsvMaybe("database/postgresql_table_counts_week10.csv");
const pgCompanyPanel = await readCsvMaybe("database/postgresql_company_panel_disclosure_week10.csv");
const pgBoardSummary = await readCsvMaybe("database/postgresql_board_summary_week10.csv");
const pgInvestorTypes = await readCsvMaybe("database/postgresql_investor_type_summary_week10.csv");
const pgFundStatus = await readCsvMaybe("database/postgresql_fund_enrichment_status_week10.csv");
const pgRegression = await readCsvMaybe("database/postgresql_regression_brief_week10.csv");
const postgresImported = pgDisclosure.length > 0;

function matrix(records, headers) {
  return [
    headers.map((h) => labels[h] || h),
    ...records.map((row) => headers.map((h) => normalize(row[h], h))),
  ];
}

function styleRange(sheet, range, headerRange) {
  sheet.getRange(range).format = {
    font: { name: "Microsoft YaHei", size: 10 },
    wrapText: true,
    verticalAlignment: "center",
    borders: {
      insideHorizontal: { style: "thin", color: "#E5E7EB" },
      bottom: { style: "thin", color: "#CBD5E1" },
    },
  };
  sheet.getRange(headerRange).format = {
    fill: "#1F4D78",
    font: { name: "Microsoft YaHei", bold: true, color: "#FFFFFF", size: 10 },
    wrapText: true,
  };
}

function writeTable(workbook, sheetName, records, headers, widths = {}) {
  const sheet = workbook.worksheets.add(sheetName);
  sheet.showGridLines = false;
  const data = matrix(records, headers);
  const rows = data.length;
  const cols = headers.length;
  const end = `${colName(cols)}${rows}`;
  sheet.getRange(`A1:${end}`).values = data;
  styleRange(sheet, `A1:${end}`, `A1:${colName(cols)}1`);
  sheet.freezePanes.freezeRows(1);
  for (let i = 1; i <= cols; i += 1) {
    const letter = colName(i);
    const header = headers[i - 1];
    sheet.getRange(`${letter}:${letter}`).format.columnWidth = widths[header] || 16;
    if (header === "stock_code") {
      sheet.getRange(`${letter}:${letter}`).format.numberFormat = "@";
    }
    if (
      header.includes("pct") ||
      header.includes("share") ||
      header.includes("rate") ||
      header.includes("hhi") ||
      header.includes("index") ||
      header.includes("coef") ||
      header.includes("error") ||
      header.includes("stat") ||
      header.includes("squared") ||
      header.includes("mean") ||
      header.includes("median") ||
      header.includes("std") ||
      header.includes("min") ||
      header.includes("max") ||
      header.includes("corr")
    ) {
      sheet.getRange(`${letter}2:${letter}${rows}`).format.numberFormat = "0.000";
    }
  }
  return sheet;
}

const workbook = Workbook.create();

const summary = workbook.worksheets.add("总览");
summary.showGridLines = false;
summary.getRange("A1:H1").merge();
summary.getRange("A1").values = [["霍泓锟第十周任务总览"]];
summary.getRange("A1").format = {
  fill: "#17365D",
  font: { name: "Microsoft YaHei", bold: true, color: "#FFFFFF", size: 16 },
};
summary.getRange("1:1").format.rowHeight = 28;
summary.getRange("A2:H2").merge();
summary.getRange("A2").values = [["研究型数据集、投资主体画像、基金补充核验队列与探索性OLS"]];
summary.getRange("A2").format = { font: { name: "Microsoft YaHei", color: "#4B5563" } };

summary.getRange("A4:C4").values = [["指标", "数值", "说明"]];
summary.getRange("A5:C13").values = [
  ["样本公司", normalize(payload.summary.company_count), "沿用第九周统一8家公司样本"],
  ["公司层研究面板", normalize(payload.summary.research_panel_rows), "一家公司一行"],
  ["投资主体画像", normalize(payload.summary.investor_profile_rows), "主体名称与类型组合"],
  ["基金补充核验队列", normalize(payload.summary.fund_queue_rows), "备案编码/GP/LP不推断"],
  ["描述统计变量", normalize(payload.summary.descriptive_variables), "公司层核心变量"],
  ["相关系数对", normalize(payload.summary.correlation_pairs), "探索变量方向"],
  ["探索性OLS模型", normalize(payload.summary.regression_models), "仅演示研究路径"],
  ["谨慎样本公司", normalize(payload.summary.caution_company_count), "披露边界或异常值标记"],
  [
    "PostgreSQL状态",
    postgresImported ? "临时库导入查询完成" : displayStatus(payload.summary.postgres_status),
    postgresImported ? "55432端口临时实例真实导入并导出查询结果" : "没有口令不伪造主库入库",
  ],
];
summary.getRange("A4:C13").format = {
  font: { name: "Microsoft YaHei", size: 10 },
  wrapText: true,
  borders: { preset: "all", style: "thin", color: "#B7C9D6" },
};
summary.getRange("A4:C4").format = {
  fill: "#D9EAF7",
  font: { name: "Microsoft YaHei", bold: true, color: "#17365D" },
};
summary.getRange("A:A").format.columnWidth = 24;
summary.getRange("B:B").format.columnWidth = 28;
summary.getRange("C:C").format.columnWidth = 48;

summary.getRange("E4:I4").values = [["板块", "公司数", "平均PE/VC强度", "平均PE/VC占比", "平均有效股东数"]];
summary.getRange(`E5:I${4 + payload.board_stats.length}`).values = payload.board_stats.map((row) => [
  row.market,
  normalize(row.company_count),
  normalize(row.avg_pevc_strength_index),
  normalize(row.avg_broad_pevc_record_share),
  normalize(row.avg_effective_shareholder_count),
]);
summary.getRange(`E4:I${4 + payload.board_stats.length}`).format = {
  font: { name: "Microsoft YaHei", size: 10 },
  borders: { preset: "all", style: "thin", color: "#B7C9D6" },
};
summary.getRange("E4:I4").format = {
  fill: "#D9EAF7",
  font: { name: "Microsoft YaHei", bold: true, color: "#17365D" },
};
summary.getRange("E:I").format.columnWidth = 18;
summary.freezePanes.freezeRows(4);

const chart = summary.charts.add("bar", summary.getRange(`E4:G${4 + payload.board_stats.length}`));
chart.title = "板块PE/VC强度与样本量";
chart.hasLegend = false;
chart.xAxis = { axisType: "textAxis", textStyle: { fontSize: 9 } };
chart.yAxis = { numberFormatCode: "0.0" };
chart.setPosition("K3", "R18");

writeTable(
  workbook,
  "研究面板",
  payload.panel,
  [
    "stock_code",
    "company_short",
    "market",
    "has_vc_or_pe",
    "broad_pevc_record_share",
    "pevc_strength_index",
    "top1_ratio_pct",
    "hhi",
    "effective_shareholder_count",
    "broad_pevc_ratio_sum_pct",
    "caution_flag",
    "analysis_sample_flag",
    "quality_gate",
  ],
  { stock_code: 14, company_short: 16, quality_gate: 14 },
);

writeTable(
  workbook,
  "主体画像Top",
  payload.investor_profile.slice(0, 80),
  [
    "investor_name",
    "investor_type_final",
    "is_broad_pevc",
    "is_fund_like_name",
    "record_count",
    "company_count",
    "companies",
    "markets",
    "source_tables",
    "manual_priority",
  ],
  { investor_name: 42, investor_type_final: 22, companies: 24, source_tables: 20, manual_priority: 26 },
);

writeTable(
  workbook,
  "基金核验队列",
  payload.fund_queue,
  [
    "investor_name",
    "investor_type_final",
    "manual_priority",
    "company_count",
    "companies",
    "markets",
    "source_tables",
    "pdf_pages_observed",
    "amac_record_code",
    "gp_name",
    "lp_structure",
    "disclosure_status",
    "next_action",
    "week10_principle",
  ],
  {
    investor_name: 46,
    manual_priority: 28,
    pdf_pages_observed: 24,
    disclosure_status: 32,
    next_action: 38,
    week10_principle: 28,
  },
);

writeTable(
  workbook,
  "数据质量",
  payload.data_quality,
  [
    "stock_code",
    "company_short",
    "market",
    "ratio_timepoints",
    "usable_ratio_timepoints",
    "invalid_ratio_timepoints",
    "abnormal_ratio_timepoints",
    "blank_ratio_timepoints",
    "week8_p1_count",
    "week9_closed_p1_count",
    "quality_gate",
    "quality_note",
  ],
  { stock_code: 14, company_short: 16, quality_note: 42 },
);

writeTable(
  workbook,
  "字段完整性",
  payload.field_completeness,
  ["table_name", "field_name", "record_count", "observed_count", "missing_count", "missing_rate", "week10_action"],
  { table_name: 16, field_name: 26, week10_action: 46 },
);

writeTable(
  workbook,
  "描述统计",
  payload.descriptive_stats,
  ["variable", "variable_label", "n", "mean", "median", "std", "min", "max", "interpretation"],
  { variable: 30, variable_label: 24, interpretation: 42 },
);

writeTable(
  workbook,
  "板块统计",
  payload.board_stats,
  [
    "market",
    "company_count",
    "avg_pevc_strength_index",
    "avg_broad_pevc_record_share",
    "avg_top1_ratio_pct",
    "avg_hhi",
    "avg_effective_shareholder_count",
    "caution_company_count",
    "week10_interpretation",
  ],
  { week10_interpretation: 44 },
);

writeTable(
  workbook,
  "相关性",
  payload.correlation.filter((row) =>
    ["pevc_strength_index", "broad_pevc_record_share", "effective_shareholder_count", "top1_ratio_pct", "hhi"].includes(row.var_left) &&
    ["pevc_strength_index", "broad_pevc_record_share", "effective_shareholder_count", "top1_ratio_pct", "hhi"].includes(row.var_right)
  ),
  ["var_left", "var_right", "n", "pearson_corr", "note"],
  { var_left: 30, var_right: 30, note: 34 },
);

writeTable(
  workbook,
  "OLS结果",
  payload.regression,
  [
    "sample_scope",
    "dependent_variable",
    "independent_variable",
    "n",
    "intercept",
    "coef_x",
    "std_error_x",
    "t_stat_x",
    "r_squared",
    "model_note",
  ],
  { dependent_variable: 30, independent_variable: 30, model_note: 42 },
);

writeTable(
  workbook,
  "研究问题",
  payload.research_questions,
  ["question_id", "research_question", "current_evidence", "current_judgement", "next_data_need"],
  { research_question: 42, current_evidence: 58, current_judgement: 36, next_data_need: 42 },
);

writeTable(
  workbook,
  "验证与数据库",
  [...payload.validation, ...payload.postgres],
  ["check_item", "check_name", "status", "result", "detail", "note"],
  { check_item: 24, check_name: 24, result: 42, detail: 64, note: 42 },
);

writeTable(
  workbook,
  "PostgreSQL结果",
  pgDisclosure.length
    ? pgDisclosure
    : [{ item: "状态", value: "未生成", source_note: "先运行database/run_postgres_temp_week10.ps1" }],
  ["item", "value", "source_note"],
  { item: 24, value: 30, source_note: 72 },
);

writeTable(
  workbook,
  "PG表行数",
  pgTableCounts,
  ["table_name", "row_count"],
  { table_name: 42, row_count: 14 },
);

writeTable(
  workbook,
  "PG公司面板",
  pgCompanyPanel,
  [
    "stock_code",
    "company_short",
    "market",
    "broad_pevc_record_share",
    "pevc_strength_index",
    "top1_ratio_pct",
    "effective_shareholder_count",
    "quality_gate",
  ],
  { company_short: 18, quality_gate: 18 },
);

writeTable(
  workbook,
  "PG板块统计",
  pgBoardSummary,
  [
    "market",
    "company_count",
    "avg_pevc_strength_index",
    "avg_broad_pevc_record_share",
    "avg_top1_ratio_pct",
    "avg_effective_shareholder_count",
    "caution_company_count",
  ],
  { market: 18, caution_company_count: 18 },
);

writeTable(
  workbook,
  "PG投资类型",
  pgInvestorTypes,
  [
    "investor_type_final",
    "investor_profile_rows",
    "source_record_count",
    "company_mentions",
    "broad_pevc_profiles",
    "fund_like_profiles",
  ],
  { investor_type_final: 28 },
);

writeTable(
  workbook,
  "PG基金状态",
  pgFundStatus,
  [
    "manual_priority",
    "fund_queue_rows",
    "amac_code_filled",
    "gp_filled",
    "lp_structure_filled",
    "disclosure_status",
  ],
  { manual_priority: 32, disclosure_status: 56 },
);

writeTable(
  workbook,
  "PG回归摘要",
  pgRegression,
  [
    "model_id",
    "sample_scope",
    "dependent_variable",
    "independent_variable",
    "n",
    "coef_x",
    "r_squared",
    "model_note",
  ],
  { dependent_variable: 30, independent_variable: 30, model_note: 42 },
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
    "研究面板",
    "基金核验队列",
    "描述统计",
    "板块统计",
    "OLS结果",
    "研究问题",
    "PostgreSQL结果",
    "PG表行数",
    "PG公司面板",
    "PG板块统计",
  ]) {
    const blob = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
    await fs.writeFile(path.join(previewDir, `${sheetName}.png`), new Uint8Array(await blob.arrayBuffer()));
  }
}

const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);
console.log(`saved ${outputPath}`);
