import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dataPath = path.join(root, "outputs", "week13_workbook_data.json");
const outputPath = path.join(root, "outputs", "霍泓锟_第十三周扩样核验结果.xlsx");
const inspectPath = `${outputPath}.inspect.ndjson`;
const previewDir = path.join(root, "outputs", "workbook_preview");
const data = JSON.parse(await fs.readFile(dataPath, "utf8"));
const tables = data.tables || {};

const font = "Microsoft YaHei";
const navy = "#1F4E78";
const blue = "#DCE6F1";
const pale = "#F4F7FA";
const border = "#D9E2F3";
const text = "#1F2937";

function colName(index) {
  let result = "";
  let value = index + 1;
  while (value > 0) {
    const remainder = (value - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    value = Math.floor((value - 1) / 26);
  }
  return result;
}

function valuesFor(rows, columns) {
  return rows.map((row) => columns.map((column) => row[column] ?? ""));
}

function writeSheet(workbook, name, title, rows, columns, labels, widths = {}, options = {}) {
  const sheet = workbook.worksheets.add(name);
  sheet.showGridLines = false;
  const lastCol = colName(columns.length - 1);
  sheet.mergeCells(`A2:${lastCol}2`);
  sheet.getRange("A2").values = [[title]];
  sheet.getRange("A2").format = { font: { name: font, size: 14, bold: true, color: "#000000" } };
  sheet.getRange(`A3:${lastCol}3`).format.borders = { bottom: { style: "thin", color: navy } };
  sheet.getRange(`A5:${lastCol}5`).values = [columns.map((column) => labels[column] || column)];
  const bodyEnd = 5 + rows.length;
  if (rows.length) sheet.getRange(`A6:${lastCol}${bodyEnd}`).values = valuesFor(rows, columns);
  sheet.getRange(`A5:${lastCol}${Math.max(5, bodyEnd)}`).format.font = { name: font, size: 10, color: text };
  sheet.getRange(`A5:${lastCol}5`).format = {
    fill: navy,
    font: { name: font, size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: "#FFFFFF" },
  };
  if (rows.length) {
    const body = sheet.getRange(`A6:${lastCol}${bodyEnd}`);
    body.format.verticalAlignment = "center";
    body.format.borders = { insideHorizontal: { style: "thin", color: border }, bottom: { style: "thin", color: border } };
    body.format.rowHeight = options.rowHeight || 22;
  }
  for (let index = 0; index < columns.length; index += 1) {
    const column = columns[index];
    const range = sheet.getRange(`${colName(index)}:${colName(index)}`);
    range.format.columnWidth = widths[column] || 18;
    if ((options.wrapColumns || []).includes(column)) range.format.wrapText = true;
  }
  if (options.freezeColumns) sheet.freezePanes.freezeColumns(options.freezeColumns);
  sheet.freezePanes.freezeRows(5);
  sheet.tabColor = options.tabColor || "#9FBAD0";
  return sheet;
}

const workbook = Workbook.create();

const summary = workbook.worksheets.add("总览");
summary.showGridLines = false;
summary.tabColor = navy;
summary.getRange("A2:H2").merge();
summary.getRange("A2").values = [["霍泓锟第十三周扩样核验结果"]];
summary.getRange("A2").format = { font: { name: font, size: 16, bold: true, color: "#000000" } };
summary.getRange("A3:H3").merge();
summary.getRange("A3").values = [["首批12家北交所公司 从页码化文本独立定位Auto候选并生成复核队列"]];
summary.getRange("A3").format = { font: { name: font, size: 10, italic: true, color: "#4B5563" } };
summary.getRange("A4:H4").format.borders = { bottom: { style: "thin", color: navy } };
summary.getRange("A6:C6").values = [["指标", "结果", "解释"]];
summary.getRange("A6:C6").format = { fill: navy, font: { name: font, bold: true, color: "#FFFFFF", size: 10 }, horizontalAlignment: "center", borders: { preset: "all", style: "thin", color: "#FFFFFF" } };
summary.getRange("A7:A15").values = [
  ["扩样公司"], ["页码化文本页数"], ["Auto候选"], ["保留候选"], ["转让系统误命中排除"],
  ["去重投资主体候选"], ["人工复核队列"], ["旧定位页平均找回率"], ["PostgreSQL导入行数"],
];
const pgTotalRows = (tables.pg_table_counts || []).reduce((sum, row) => sum + Number(row.row_count || 0), 0);
summary.getRange("J6:K6").values = [["计算基础", "来源"]];
summary.getRange("J7:K15").values = [
  [data.summary.selected_company_count, "selected_company_count"],
  [data.summary.source_page_count, "source_page_count"],
  [data.summary.auto_candidate_record_count, "auto_candidate_record_count"],
  [data.summary.retained_candidate_record_count, "retained_candidate_record_count"],
  [data.summary.excluded_transfer_boilerplate_count, "excluded_transfer_boilerplate_count"],
  [data.summary.unique_investor_candidate_count, "unique_investor_candidate_count"],
  [data.summary.manual_review_queue_count, "manual_review_queue_count"],
  [data.summary.old_candidate_average_page_recovery_rate, "old_candidate_average_page_recovery_rate"],
  [pgTotalRows, "PostgreSQL table count sum"],
];
for (let row = 7; row <= 15; row += 1) summary.getRange(`B${row}`).formulas = [[`=J${row}`]];
summary.getRange("C7:C15").values = [
  ["第十二周P1队列中关键词命中排名前12"], ["每家公司保留180页页码化文本"], ["含保留和规则排除记录"],
  ["仍需人工核对后进入Gold"], ["没有明确交易主体的公开转让语境"], ["名称与类型均为候选，深度字段留空"],
  ["低/中置信及转让、备案候选优先"], ["定位一致性，不是Gold准确率"], ["临时PostgreSQL 11张表合计"],
];
summary.getRange("A7:C15").format = { font: { name: font, size: 10, color: text }, verticalAlignment: "center", borders: { insideHorizontal: { style: "thin", color: border }, bottom: { style: "thin", color: border } } };
summary.getRange("B14").format.numberFormat = "0.0%";
summary.getRange("A:A").format.columnWidth = 30;
summary.getRange("B:B").format.columnWidth = 18;
summary.getRange("C:C").format.columnWidth = 60;
summary.getRange("E6:H6").values = [["事件类型", "候选记录", "覆盖公司", "高置信记录"]];
summary.getRange("E6:H6").format = { fill: navy, font: { name: font, bold: true, color: "#FFFFFF", size: 10 }, horizontalAlignment: "center", borders: { preset: "all", style: "thin", color: "#FFFFFF" } };
summary.getRange("E7:H11").values = valuesFor(tables.event_summary || [], ["event_type", "candidate_records", "companies_covered", "high_confidence_records"]);
summary.getRange("E7:H11").format = { font: { name: font, size: 10, color: text }, verticalAlignment: "center", borders: { insideHorizontal: { style: "thin", color: border }, bottom: { style: "thin", color: border } } };
summary.getRange("E:E").format.columnWidth = 24;
summary.getRange("F:H").format.columnWidth = 16;
summary.getRange("E13:H13").merge();
summary.getRange("E13").values = [["使用边界"]];
summary.getRange("E13").format = { fill: blue, font: { name: font, bold: true, color: "#000000" } };
summary.getRange("E14:H16").merge();
summary.getRange("E14").values = [["本工作簿展示Auto定位和候选结果。备案编码、GP、LP结构未由招股书明确披露时保持空值；投资主体类型和事件记录需回原文页人工确认后才能进入Gold/Final。"]];
summary.getRange("E14:H16").format = { font: { name: font, size: 10, color: text }, wrapText: true, verticalAlignment: "center", fill: pale };
summary.getRange("J6:K6").format = { fill: blue, font: { name: font, size: 9, bold: true, color: "#000000" } };
summary.getRange("J7:K15").format = { font: { name: font, size: 9, color: text }, borders: { insideHorizontal: { style: "thin", color: border } } };
summary.getRange("J14").format.numberFormat = "0.0%";
summary.getRange("J:J").format.columnWidth = 18;
summary.getRange("K:K").format.columnWidth = 42;

writeSheet(workbook, "公司进度", "12家公司处理进度", tables.company_progress || [],
  ["stock_code", "company_short", "page_count", "chapter_groups_located", "retained_auto_candidates", "excluded_transfer_boilerplate", "investor_name_candidates", "high_confidence_candidates", "processing_status"],
  { stock_code: "股票代码", company_short: "公司简称", page_count: "文本页数", chapter_groups_located: "定位章节组", retained_auto_candidates: "保留候选", excluded_transfer_boilerplate: "排除误命中", investor_name_candidates: "主体原始候选", high_confidence_candidates: "高置信候选", processing_status: "处理状态" },
  { processing_status: 42 }, { wrapColumns: ["processing_status"], freezeColumns: 2, tabColor: "#5B9BD5" });

writeSheet(workbook, "事件汇总", "Auto事件候选汇总", tables.event_summary || [],
  ["event_code", "event_type", "candidate_records", "companies_covered", "high_confidence_records", "with_date", "with_amount_or_shares", "use_note"],
  { event_code: "事件代码", event_type: "事件类型", candidate_records: "候选记录", companies_covered: "覆盖公司", high_confidence_records: "高置信记录", with_date: "含日期", with_amount_or_shares: "含金额或股数", use_note: "使用说明" },
  { use_note: 58 }, { wrapColumns: ["use_note"] });

writeSheet(workbook, "章节定位", "章节定位与页码索引", tables.chapter_locator || [],
  ["stock_code", "company_short", "chapter_group", "located", "first_page", "top_pages", "matched_terms", "hit_pages_count"],
  { stock_code: "股票代码", company_short: "公司简称", chapter_group: "章节组", located: "是否定位", first_page: "首个页码", top_pages: "重点页码", matched_terms: "命中词", hit_pages_count: "命中页数" },
  { chapter_group: 26, top_pages: 30, matched_terms: 42 }, { wrapColumns: ["matched_terms"], freezeColumns: 2 });

writeSheet(workbook, "Auto证据候选", "Auto证据候选明细", tables.auto_evidence || [],
  ["candidate_id", "stock_code", "company_short", "event_type", "source_page", "matched_term", "date_text", "amount_text", "shares_text", "ratio_text", "confidence", "auto_status", "evidence_preview"],
  { candidate_id: "候选ID", stock_code: "股票代码", company_short: "公司简称", event_type: "事件类型", source_page: "页码", matched_term: "命中词", date_text: "日期文本", amount_text: "金额文本", shares_text: "股数文本", ratio_text: "比例文本", confidence: "置信度", auto_status: "Auto状态", evidence_preview: "证据预览" },
  { candidate_id: 24, date_text: 22, amount_text: 24, shares_text: 20, auto_status: 26, evidence_preview: 78 },
  { wrapColumns: ["auto_status", "evidence_preview"], freezeColumns: 3, rowHeight: 38 });

writeSheet(workbook, "投资主体候选", "去重投资主体与类型候选", tables.investor_profile || [],
  ["profile_id", "stock_code", "company_short", "investor_name_candidate", "investor_type_candidate", "is_pevc_candidate", "classification_basis", "evidence_pages", "occurrence_count", "manual_review_status", "amac_filing_code", "gp_name", "lp_structure", "deep_field_rule"],
  { profile_id: "主体ID", stock_code: "股票代码", company_short: "公司简称", investor_name_candidate: "投资主体候选", investor_type_candidate: "类型候选", is_pevc_candidate: "PEVC候选", classification_basis: "分类依据", evidence_pages: "证据页", occurrence_count: "出现次数", manual_review_status: "人工状态", amac_filing_code: "备案编码", gp_name: "GP", lp_structure: "LP结构", deep_field_rule: "深度字段原则" },
  { investor_name_candidate: 42, classification_basis: 58, evidence_pages: 26, manual_review_status: 20, amac_filing_code: 22, gp_name: 24, lp_structure: 28, deep_field_rule: 40 },
  { wrapColumns: ["classification_basis", "deep_field_rule"], freezeColumns: 3 });

writeSheet(workbook, "人工复核队列", "人工复核抽样队列", tables.manual_review || [],
  ["review_id", "priority", "candidate_id", "stock_code", "company_short", "event_type", "source_page", "confidence", "review_reason", "human_decision", "corrected_value", "reviewer", "review_date", "evidence_preview"],
  { review_id: "复核ID", priority: "优先级", candidate_id: "候选ID", stock_code: "股票代码", company_short: "公司简称", event_type: "事件类型", source_page: "页码", confidence: "置信度", review_reason: "复核原因", human_decision: "人工结论", corrected_value: "修正值", reviewer: "复核人", review_date: "复核日期", evidence_preview: "证据预览" },
  { review_reason: 48, human_decision: 20, corrected_value: 28, evidence_preview: 78 },
  { wrapColumns: ["review_reason", "corrected_value", "evidence_preview"], freezeColumns: 3, rowHeight: 42 });

const cross = writeSheet(workbook, "旧新定位对比", "第三周旧定位与第十三周定位对比", tables.crosscheck || [],
  ["stock_code", "company_short", "old_candidate_record_count", "old_unique_pages", "week13_retained_records", "week13_unique_pages", "overlap_pages", "old_page_recovery_rate", "newly_located_pages", "comparison_scope"],
  { stock_code: "股票代码", company_short: "公司简称", old_candidate_record_count: "旧候选记录", old_unique_pages: "旧定位页", week13_retained_records: "本周保留记录", week13_unique_pages: "本周定位页", overlap_pages: "重合页", old_page_recovery_rate: "旧页找回率", newly_located_pages: "新增定位页", comparison_scope: "比较口径" },
  { comparison_scope: 44 }, { wrapColumns: ["comparison_scope"], freezeColumns: 2 });
cross.getRange("H6:H17").format.numberFormat = "0.0%";

writeSheet(workbook, "数据来源", "入选公司与来源追踪", tables.selected_companies || [],
  ["batch_order", "queue_id", "stock_code", "company_short", "board", "source_platform", "source_url", "original_text_path", "package_text_file", "page_count", "week12_keyword_hits", "selection_reason", "missing_policy"],
  { batch_order: "批次顺序", queue_id: "队列ID", stock_code: "股票代码", company_short: "公司简称", board: "板块", source_platform: "来源平台", source_url: "招股书URL", original_text_path: "原始文本路径", package_text_file: "包内文本路径", page_count: "页数", week12_keyword_hits: "关键词命中", selection_reason: "入选原因", missing_policy: "缺失值原则" },
  { source_platform: 38, source_url: 68, original_text_path: 68, package_text_file: 54, selection_reason: 62, missing_policy: 58 },
  { wrapColumns: ["source_platform", "source_url", "original_text_path", "selection_reason", "missing_policy"], freezeColumns: 4, rowHeight: 48, tabColor: "#A5A5A5" });

writeSheet(workbook, "分类规则", "investor_type分类规则", tables.investor_type_rules || [],
  ["type", "positive_rule", "negative_rule", "final_requirement"],
  { type: "类型", positive_rule: "正向规则", negative_rule: "不得直接归类的情形", final_requirement: "Final要求" },
  { type: 24, positive_rule: 62, negative_rule: 62, final_requirement: 52 },
  { wrapColumns: ["positive_rule", "negative_rule", "final_requirement"], rowHeight: 44, tabColor: "#A5A5A5" });

writeSheet(workbook, "PG披露结果", "PostgreSQL导入与查询披露", tables.pg_disclosure || [],
  ["item", "value", "source_note"], { item: "项目", value: "结果", source_note: "来源说明" },
  { item: 34, value: 26, source_note: 66 }, { wrapColumns: ["source_note"], tabColor: "#70AD47" });

writeSheet(workbook, "PG表行数", "PostgreSQL表行数", tables.pg_table_counts || [],
  ["table_name", "row_count"], { table_name: "表名", row_count: "行数" },
  { table_name: 48, row_count: 16 }, { tabColor: "#70AD47" });

writeSheet(workbook, "质量验证", "第十三周质量验证", tables.validation || [],
  ["check_item", "status", "value", "rule"], { check_item: "检查项", status: "状态", value: "结果", rule: "验收规则" },
  { check_item: 36, status: 14, value: 26, rule: 70 }, { wrapColumns: ["rule"], tabColor: "#FFC000" });

writeSheet(workbook, "本周执行计划", "第十三周执行记录", tables.weekly_plan || [],
  ["day", "task", "action", "output", "status"], { day: "日期", task: "任务", action: "操作", output: "产出", status: "状态" },
  { day: 16, task: 28, action: 78, output: 42, status: 18 }, { wrapColumns: ["action", "output"], rowHeight: 42 });

workbook.recalculate();
const keyInspect = await workbook.inspect({ kind: "table,formula", sheetId: "总览", range: "A2:H16", maxChars: 12000, tableMaxRows: 20, tableMaxCols: 10 });
const errorInspect = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!", options: { useRegex: true, maxResults: 300 }, summary: "final formula error scan" });
await fs.writeFile(inspectPath, `${keyInspect.ndjson}\n${errorInspect.ndjson}`);

await fs.mkdir(previewDir, { recursive: true });
for (const sheet of workbook.worksheets.items) {
  const blob = await workbook.render({ sheetName: sheet.name, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(path.join(previewDir, `${sheet.name}.png`), new Uint8Array(await blob.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`saved ${outputPath}`);
// Artifact Tool can leave a non-zero process status after non-fatal renderer diagnostics.
// Reaching this line means inspection, all sheet previews, and XLSX export completed.
process.exit(0);
