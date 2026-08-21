import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(path.join(path.dirname(fileURLToPath(import.meta.url)), ".."));
const payload = JSON.parse(await fs.readFile(path.join(root, "outputs", "week9_workbook_data.json"), "utf8"));
const outputPath = path.join(root, "outputs", "week9_summary_workbook.xlsx");
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

const LABELS = {
  queue_id: "编号",
  stock_code: "证券代码",
  company_short: "公司简称",
  market: "板块",
  source: "来源",
  issue_type: "问题类型",
  week8_status: "第八周状态",
  week9_resolution: "第九周处理结论",
  data_action: "数据处理动作",
  analysis_action: "分析处理动作",
  evidence_principle: "证据原则",
  remaining_risk: "剩余风险",
  has_vc_or_pe: "是否有VC/PE",
  vc_record_count: "VC记录数",
  pe_record_count: "PE记录数",
  broad_pevc_record_count: "广义PE/VC记录数",
  broad_pevc_record_share: "广义PE/VC记录占比",
  pevc_intensity_level: "PE/VC强度",
  distinct_investor_type_count: "投资主体类型数",
  week8_p1_item_count: "第八周P1项",
  week9_closed_p1_count: "第九周闭环P1项",
  week9_unresolved_p1_count: "第九周未闭环P1项",
  transfer_event_count: "转让事件数",
  top1_ratio_pct: "第一大股东比例",
  top3_ratio_pct: "前三大股东比例",
  hhi: "HHI",
  effective_shareholder_count: "有效股东数",
  broad_pevc_holder_count: "广义PE/VC股东数",
  broad_pevc_ratio_sum_pct: "广义PE/VC持股比例",
  dispersion_level: "分散度判断",
  week9_research_note: "研究使用说明",
  selected_time_point: "选取时点",
  shareholder_count: "股东数",
  analysis_note: "分析说明",
  company_count: "公司数",
  vc_pe_supported_count: "有VC/PE公司数",
  avg_broad_pevc_record_share: "平均PE/VC记录占比",
  avg_distinct_investor_type_count: "平均主体类型数",
  avg_top1_ratio_pct: "平均第一大股东比例",
  avg_effective_shareholder_count: "平均有效股东数",
  week9_interpretation: "口径说明",
  investor_type: "投资主体类型",
  table_role: "表内角色",
  record_count: "记录数",
  is_broad_pevc: "是否广义PE/VC",
  research_question: "研究问题",
  current_conclusion: "当前观察",
  check_name: "检查项",
  status: "状态",
  detail: "说明",
};

function normalize(value, header = "") {
  if (header === "stock_code") {
    const text = String(value ?? "").trim();
    return text.padStart(6, "0");
  }
  if (value === undefined || value === null || Number.isNaN(value)) return null;
  if (value === "") return null;
  if (typeof value === "string" && /^-?\d+(\.\d+)?$/.test(value.trim()) && !/^0\d+/.test(value.trim())) {
    return Number(value);
  }
  return value;
}

function matrixFromRecords(records, headers) {
  return [headers.map((h) => LABELS[h] || h), ...records.map((row) => headers.map((h) => normalize(row[h], h)))];
}

function writeTable(workbook, sheetName, records, headers, widths = {}) {
  const sheet = workbook.worksheets.add(sheetName);
  sheet.showGridLines = false;
  const matrix = matrixFromRecords(records, headers);
  const rows = matrix.length;
  const cols = headers.length;
  const end = `${colName(cols)}${rows}`;
  sheet.getRange(`A1:${end}`).values = matrix;
  sheet.getRange(`A1:${colName(cols)}1`).format = {
    fill: "#1F4D78",
    font: { bold: true, color: "#FFFFFF" },
    wrapText: true,
  };
  sheet.getRange(`A1:${end}`).format.borders = {
    insideHorizontal: { style: "thin", color: "#E5E7EB" },
    bottom: { style: "thin", color: "#CBD5E1" },
  };
  sheet.getRange(`A1:${end}`).format.wrapText = true;
  sheet.freezePanes.freezeRows(1);
  for (let c = 1; c <= cols; c += 1) {
    const letter = colName(c);
    const header = headers[c - 1];
    sheet.getRange(`${letter}:${letter}`).format.columnWidth = widths[header] || 15;
    if (header === "stock_code") {
      sheet.getRange(`${letter}:${letter}`).format.numberFormat = "@";
      if (rows > 1) {
        sheet.getRange(`${letter}2:${letter}${rows}`).formulas = records.map((row) => [
          `="${String(row[header] ?? "").padStart(6, "0")}"`,
        ]);
      }
    }
  }
  return sheet;
}

const workbook = Workbook.create();

const summary = workbook.worksheets.add("总览");
summary.showGridLines = false;
summary.getRange("A1:H1").merge();
summary.getRange("A1").values = [["霍泓锟第九周任务总览"]];
summary.getRange("A1").format = {
  fill: "#17365D",
  font: { bold: true, color: "#FFFFFF", size: 16 },
};
summary.getRange("1:1").format.rowHeight = 28;
summary.getRange("A2:H2").merge();
summary.getRange("A2").values = [["P1复核闭环、PostgreSQL导入准备与PE/VC研究变量形成"]];
summary.getRange("A2").format = { font: { color: "#4B5563" } };
summary.getRange("2:2").format.rowHeight = 22;

summary.getRange("A4:C4").values = [["指标", "数值", "说明"]];
summary.getRange("A5:C13").values = [
  ["样本公司", normalize(payload.summary.company_count), "沿用统一8家公司样本"],
  ["认缴/增资记录", normalize(payload.summary.subscription_records), "来自第八周清洗表"],
  ["股权快照记录", normalize(payload.summary.snapshot_records), "来自第八周清洗表"],
  ["股权转让记录", normalize(payload.summary.transfer_records), "来自第八周清洗表"],
  ["第八周P1复核项", normalize(payload.summary.week8_p1_items), "本周逐条闭环处理"],
  ["第九周已闭环P1项", normalize(payload.summary.week9_closed_p1), "闭环不等于补数"],
  ["第九周未闭环P1项", normalize(payload.summary.week9_unresolved_p1), "当前为0"],
  ["研究变量公司数", normalize(payload.summary.research_company_count), "用于描述性研究问题"],
  ["PostgreSQL状态", payload.summary.postgres_status, "服务可用，导入需密码"],
];
summary.getRange("A4:C4").format = {
  fill: "#D9EAF7",
  font: { bold: true, color: "#17365D" },
};
summary.getRange("A4:C13").format.borders = { preset: "all", style: "thin", color: "#B7C9D6" };
summary.getRange("A:A").format.columnWidth = 24;
summary.getRange("B:B").format.columnWidth = 24;
summary.getRange("C:C").format.columnWidth = 54;

summary.getRange("E4:H4").values = [["板块", "公司数", "平均PE/VC占比", "平均有效股东数"]];
summary.getRange(`E5:H${4 + payload.board_stats.length}`).values = payload.board_stats.map((row) => [
  row.market,
  normalize(row.company_count, "company_count"),
  normalize(row.avg_broad_pevc_record_share, "avg_broad_pevc_record_share"),
  normalize(row.avg_effective_shareholder_count, "avg_effective_shareholder_count"),
]);
summary.getRange("E4:H4").format = {
  fill: "#D9EAF7",
  font: { bold: true, color: "#17365D" },
};
summary.getRange(`E4:H${4 + payload.board_stats.length}`).format.borders = {
  preset: "all",
  style: "thin",
  color: "#B7C9D6",
};
summary.getRange("E:H").format.columnWidth = 18;
summary.freezePanes.freezeRows(4);

writeTable(
  workbook,
  "复核闭环",
  payload.review_resolved,
  [
    "queue_id",
    "stock_code",
    "company_short",
    "market",
    "issue_type",
    "week8_status",
    "week9_resolution",
    "data_action",
    "analysis_action",
    "evidence_principle",
    "remaining_risk",
  ],
  {
    queue_id: 16,
    company_short: 16,
    issue_type: 24,
    week9_resolution: 24,
    data_action: 38,
    analysis_action: 44,
    evidence_principle: 24,
    remaining_risk: 44,
  },
);

writeTable(
  workbook,
  "研究变量",
  payload.research_variables,
  [
    "stock_code",
    "company_short",
    "market",
    "has_vc_or_pe",
    "broad_pevc_record_share",
    "pevc_intensity_level",
    "distinct_investor_type_count",
    "week8_p1_item_count",
    "week9_closed_p1_count",
    "week9_unresolved_p1_count",
    "top1_ratio_pct",
    "hhi",
    "effective_shareholder_count",
    "dispersion_level",
    "week9_research_note",
  ],
  {
    company_short: 16,
    broad_pevc_record_share: 20,
    distinct_investor_type_count: 24,
    effective_shareholder_count: 24,
    week9_research_note: 42,
  },
);

writeTable(
  workbook,
  "股权分散度",
  payload.ownership_metrics,
  [
    "stock_code",
    "company_short",
    "market",
    "selected_time_point",
    "shareholder_count",
    "top1_ratio_pct",
    "top3_ratio_pct",
    "hhi",
    "effective_shareholder_count",
    "broad_pevc_holder_count",
    "broad_pevc_ratio_sum_pct",
    "dispersion_level",
    "analysis_note",
  ],
  {
    selected_time_point: 26,
    effective_shareholder_count: 24,
    broad_pevc_ratio_sum_pct: 24,
    analysis_note: 36,
  },
);

writeTable(
  workbook,
  "板块统计",
  payload.board_stats,
  [
    "market",
    "company_count",
    "vc_pe_supported_count",
    "avg_broad_pevc_record_share",
    "avg_distinct_investor_type_count",
    "avg_top1_ratio_pct",
    "avg_effective_shareholder_count",
    "week9_interpretation",
  ],
  {
    avg_broad_pevc_record_share: 24,
    avg_distinct_investor_type_count: 26,
    avg_effective_shareholder_count: 26,
    week9_interpretation: 42,
  },
);

writeTable(
  workbook,
  "投资主体矩阵",
  payload.investor_matrix,
  ["market", "investor_type", "table_role", "record_count", "is_broad_pevc"],
  { investor_type: 28, table_role: 16, is_broad_pevc: 16 },
);

writeTable(
  workbook,
  "研究问题观察",
  payload.research_rows,
  [
    "research_question",
    "stock_code",
    "company_short",
    "market",
    "pevc_intensity_level",
    "broad_pevc_record_share",
    "top1_ratio_pct",
    "effective_shareholder_count",
    "dispersion_level",
    "current_conclusion",
  ],
  {
    research_question: 48,
    company_short: 16,
    effective_shareholder_count: 24,
    current_conclusion: 46,
  },
);

writeTable(
  workbook,
  "数据库状态",
  payload.postgres_audit,
  ["check_name", "status", "detail"],
  { check_name: 22, status: 22, detail: 70 },
);

if (process.argv.includes("--render")) {
  await fs.mkdir(previewDir, { recursive: true });
  for (const sheetName of [
    "总览",
    "复核闭环",
    "研究变量",
    "股权分散度",
    "板块统计",
    "投资主体矩阵",
    "研究问题观察",
    "数据库状态",
  ]) {
    const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
    await fs.writeFile(path.join(previewDir, `${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
  }
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`saved ${outputPath}`);
process.exit(0);
