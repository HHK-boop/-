from __future__ import annotations

import csv
import json
import shutil
from datetime import date
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parents[1]
WEEK6 = next(p for p in ROOT.iterdir() if p.name.startswith("week6_submission"))
OLD_WEEK7 = next((p for p in ROOT.iterdir() if "VCPE" in p.name and "第七周" in p.name), None)


ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "gbk")


def read_csv_auto(path: Path) -> pd.DataFrame:
    last = None
    for enc in ENCODINGS:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception as exc:  # noqa: BLE001
            last = exc
    raise RuntimeError(f"Cannot read CSV: {path}") from last


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def norm_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def infer_market(stock_code) -> str:
    s = str(stock_code).strip().zfill(6)
    if s.startswith("920"):
        return "北交所"
    if s.startswith("688"):
        return "科创板"
    if s.startswith("301") or s.startswith("300"):
        return "创业板"
    if s.startswith("603") or s.startswith("001") or s.startswith("00"):
        return "主板"
    return "待确认"


def classify_investor(name, auto_type="") -> tuple[str, str, str]:
    name = norm_text(name)
    auto_type = norm_text(auto_type)
    text = f"{name} {auto_type}"
    if not name:
        return "", "未识别主体", "主体名称为空，保留空值"
    if "员工持股" in text or "持股平台" in text or "员工" in text and "平台" in text:
        return "员工持股平台", "规则命中", "名称或原分类包含员工持股/持股平台"
    if "自然人" in auto_type or ("公司" not in name and "合伙" not in name and "基金" not in name and "投资" not in name and len(name) <= 4):
        return "自然人", "规则命中", "自然人姓名或原分类为自然人/其他"
    if any(k in text for k in ["控股股东", "实际控制人", "创始人"]):
        return "控股股东/实际控制人", "规则命中", "原分类或证据提示控股股东/实际控制人"
    if any(k in text for k in ["国资", "财政", "政府", "引导基金", "国有", "国投", "高新投"]):
        return "政府基金/国资平台", "规则命中", "名称包含国资、政府、财政、引导基金等"
    if any(k in text for k in ["创业投资", "创投", "风险投资", "科技创业"]):
        return "VC", "规则命中", "名称包含创业投资/创投/风险投资"
    if any(k in text for k in ["私募", "股权投资基金", "投资基金", "股权投资", "资本管理", "资产管理"]):
        return "PE", "规则命中", "名称包含私募、股权投资、投资基金或资本管理"
    if any(k in text for k in ["产业资本", "法人股东", "有限公司", "股份有限公司", "集团", "实业", "产业"]):
        return "产业资本/CVC/法人股东", "规则命中", "企业法人或原分类提示产业资本/法人股东"
    if "合伙企业" in text or "合伙" in text:
        return "其他投资平台", "人工复核", "合伙企业但未披露基金/员工持股/政府属性"
    return "其他/待人工复核", "人工复核", "名称无法稳定判断具体类别"


def add_investor_type(df: pd.DataFrame, name_col: str) -> pd.DataFrame:
    result = df.copy()
    auto_col = "investor_type_auto" if "investor_type_auto" in result.columns else None
    types, methods, reasons = [], [], []
    for _, row in result.iterrows():
        inv_type, method, reason = classify_investor(
            row.get(name_col, ""), row.get(auto_col, "") if auto_col else ""
        )
        types.append(inv_type)
        methods.append(method)
        reasons.append(reason)
    result["investor_type_final"] = types
    result["investor_type_method"] = methods
    result["investor_type_reason"] = reasons
    return result


def missing_summary(df: pd.DataFrame, table_name: str, important_cols: list[str]) -> pd.DataFrame:
    rows = []
    for col in important_cols:
        if col in df.columns:
            missing = int(df[col].isna().sum() + (df[col].astype(str).str.strip() == "").sum())
            rows.append(
                {
                    "table_name": table_name,
                    "field": col,
                    "records": len(df),
                    "missing_count": missing,
                    "missing_rate": round(missing / len(df), 4) if len(df) else 0,
                    "week7_principle": "PDF未披露则留空，不用0或外部资料补值",
                }
            )
    return pd.DataFrame(rows)


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_text(cell, text: str, bold: bool = False) -> None:
    cell.text = ""
    p = cell.paragraphs[0]
    run = p.add_run(str(text))
    run.bold = bold
    run.font.name = "Microsoft YaHei"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    run.font.size = Pt(9)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def add_table(doc: Document, headers: list[str], rows: list[list[str]]) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    for i, header in enumerate(headers):
        set_cell_text(table.rows[0].cells[i], header, bold=True)
        set_cell_shading(table.rows[0].cells[i], "E8EEF5")
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            set_cell_text(cells[i], value)
    doc.add_paragraph()


def add_heading(doc: Document, text: str, level: int) -> None:
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        run.font.name = "Microsoft YaHei"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
        run.font.color.rgb = RGBColor(46, 116, 181)


def add_para(doc: Document, text: str) -> None:
    p = doc.add_paragraph(text)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.15
    for run in p.runs:
        run.font.name = "Microsoft YaHei"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
        run.font.size = Pt(10.5)


def build_docx(report_path: Path, stats: dict, issue_rows: list[dict], type_rows: pd.DataFrame) -> None:
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Inches(1)
    sec.bottom_margin = Inches(1)
    sec.left_margin = Inches(1)
    sec.right_margin = Inches(1)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("第七周任务汇报：PE/VC 招股书三表数据治理与数据库化准备")
    run.bold = True
    run.font.name = "Microsoft YaHei"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    run.font.size = Pt(18)
    run.font.color.rgb = RGBColor(31, 77, 120)

    meta = doc.add_paragraph("姓名：霍泓锟    日期：2026-08-01    主题：数据质量复核、investor_type统一、互查差异与PostgreSQL草案")
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for r in meta.runs:
        r.font.name = "Microsoft YaHei"
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
        r.font.size = Pt(9)

    add_heading(doc, "一、本周任务定位", 1)
    add_para(
        doc,
        "本周承接前六周的招股书PDF获取、Markdown表格解析、三表抽取、Gold/Auto/Final对比和组内互查工作，"
        "重点不再是简单增加文件数量，而是提高现有8家公司数据的可信度和可复现性。处理原则是：Auto结果必须来自PDF或Markdown，"
        "Final允许人工复核但必须保留修改原因和PDF证据；PDF未披露的金额、比例、单价等字段保留空值，不用0或外部资料补齐。",
    )

    add_heading(doc, "二、核心数据概览", 1)
    add_table(
        doc,
        ["项目", "结果"],
        [
            ["统一样本公司数", str(stats["company_count"])],
            ["认缴/增资记录", str(stats["subscription_rows"])],
            ["股权快照记录", str(stats["snapshot_rows"])],
            ["股权转让记录", str(stats["transfer_rows"])],
            ["Cross-check通过/提示/复核", f"{stats['pass_count']} / {stats['info_count']} / {stats['review_count']}"],
            ["本周新增重点", "investor_type_final、数据库表结构、问题记录表、导入计划"],
        ],
    )

    add_heading(doc, "三、investor_type分类口径", 1)
    add_para(
        doc,
        "本周将投资主体类型统一为自然人、员工持股平台、控股股东/实际控制人、政府基金/国资平台、VC、PE、产业资本/CVC/法人股东和其他/待人工复核。"
        "分类先使用名称关键词和上一版investor_type_auto，不能稳定判断时标记为人工复核，避免把所有投资主体粗糙地归为PE/VC。",
    )
    type_preview = type_rows[["investor_type_final", "record_count", "share"]].head(10)
    add_table(doc, ["类型", "记录数", "占比"], type_preview.astype(str).values.tolist())

    add_heading(doc, "四、本周发现的问题", 1)
    rows = [[r["issue_id"], r["company_short"], r["issue_type"], r["week7_action"]] for r in issue_rows[:8]]
    add_table(doc, ["编号", "公司/对象", "问题类型", "处理方式"], rows)
    add_para(
        doc,
        "目前主要问题集中在三类：一是招股书未直接披露单价或股份数，只能保留金额或出资额；二是部分股权快照的比例口径不是同一总股本口径，"
        "需要人工回到原PDF确认；三是转让事件数量少但误命中风险较高，需要用证据句和页码逐条确认。",
    )

    add_heading(doc, "五、PostgreSQL表结构准备", 1)
    add_para(
        doc,
        "本周建立了数据库草案，包括companies、investors、subscription_events、equity_snapshots、transfer_events、evidence_sources和validation_results。"
        "设计目标不是立刻做复杂实证，而是先保证三表数据可以按公司、投资主体、事件和证据四条线追溯。",
    )

    add_heading(doc, "六、下一步", 1)
    add_para(
        doc,
        "下一周建议优先完成两件事：第一，将本周生成的Week7 CSV导入PostgreSQL进行真实导入测试；第二，对REVIEW项逐条回到PDF复核，"
        "特别是黄山谷捷部分快照比例缺失、赛分科技比例合计异常、星图测控代持解除拆分等问题。之后再进入描述性统计和研究问题构建。",
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(report_path)


def main() -> None:
    (OUT / "data").mkdir(exist_ok=True)
    (OUT / "database").mkdir(exist_ok=True)
    (OUT / "review").mkdir(exist_ok=True)
    (OUT / "report").mkdir(exist_ok=True)

    sub = read_csv_auto(WEEK6 / "final" / "subscription_final.csv")
    snap = read_csv_auto(WEEK6 / "final" / "equity_snapshot_final.csv")
    tr = read_csv_auto(WEEK6 / "final" / "transfer_final.csv")
    cross = read_csv_auto(WEEK6 / "validation" / "cross_check.csv")
    auto_vs_gold = read_csv_auto(WEEK6 / "validation" / "auto_vs_gold.csv")
    intra = read_csv_auto(WEEK6 / "review" / "intra_group_review.csv")

    sub2 = add_investor_type(sub, "subscriber_name")
    snap2 = add_investor_type(snap, "shareholder_name")
    tr2 = tr.copy()
    for role, col in [("transferor", "transferor_name"), ("transferee", "transferee_name")]:
        final_types, methods, reasons = [], [], []
        for _, row in tr2.iterrows():
            inv_type, method, reason = classify_investor(row.get(col, ""))
            final_types.append(inv_type)
            methods.append(method)
            reasons.append(reason)
        tr2[f"{role}_type_final"] = final_types
        tr2[f"{role}_type_method"] = methods
        tr2[f"{role}_type_reason"] = reasons

    write_csv(sub2, OUT / "data" / "subscription_week7_final.csv")
    write_csv(snap2, OUT / "data" / "equity_snapshot_week7_final.csv")
    write_csv(tr2, OUT / "data" / "transfer_week7_final.csv")

    companies = (
        pd.concat(
            [
                sub2[["stock_code", "company_short"]],
                snap2[["stock_code", "company_short"]],
                tr2[["stock_code", "company_short"]],
            ],
            ignore_index=True,
        )
        .drop_duplicates()
        .sort_values("stock_code")
    )
    companies["stock_code"] = companies["stock_code"].astype(str).str.zfill(6)
    companies["market"] = companies["stock_code"].apply(infer_market)
    companies["week7_scope"] = "统一8家公司样本"
    write_csv(companies, OUT / "data" / "companies_week7_manifest.csv")

    type_frames = []
    type_frames.append(sub2[["stock_code", "company_short", "investor_type_final"]].assign(source_table="subscription"))
    type_frames.append(snap2[["stock_code", "company_short", "investor_type_final"]].assign(source_table="equity_snapshot"))
    type_all = pd.concat(type_frames, ignore_index=True)
    type_stats = (
        type_all.groupby(["investor_type_final"], dropna=False)
        .size()
        .reset_index(name="record_count")
        .sort_values("record_count", ascending=False)
    )
    type_stats["share"] = (type_stats["record_count"] / type_stats["record_count"].sum()).round(4)
    write_csv(type_stats, OUT / "data" / "investor_type_stats.csv")

    company_stats = []
    for code, grp in companies.groupby("stock_code"):
        short = grp["company_short"].iloc[0]
        company_stats.append(
            {
                "stock_code": code,
                "company_short": short,
                "market": grp["market"].iloc[0],
                "subscription_records": int((sub2["stock_code"].astype(str).str.zfill(6) == code).sum()),
                "snapshot_records": int((snap2["stock_code"].astype(str).str.zfill(6) == code).sum()),
                "transfer_records": int((tr2["stock_code"].astype(str).str.zfill(6) == code).sum()),
            }
        )
    company_stats_df = pd.DataFrame(company_stats)
    write_csv(company_stats_df, OUT / "data" / "company_record_summary.csv")

    missing = pd.concat(
        [
            missing_summary(
                sub2,
                "subscription",
                [
                    "pdf_page",
                    "event_date",
                    "subscriber_name",
                    "subscription_shares_wan",
                    "subscription_amount_wan",
                    "subscription_price_yuan",
                    "source_evidence",
                    "investor_type_final",
                ],
            ),
            missing_summary(
                snap2,
                "equity_snapshot",
                [
                    "pdf_page",
                    "time_point",
                    "shareholder_name",
                    "shares_held_wan",
                    "capital_contribution_wan",
                    "shareholding_ratio_pct",
                    "source_evidence",
                    "investor_type_final",
                ],
            ),
            missing_summary(
                tr2,
                "transfer",
                [
                    "pdf_page",
                    "transfer_date",
                    "transferor_name",
                    "transferee_name",
                    "transferred_shares_wan",
                    "transfer_amount_wan",
                    "transfer_price_yuan",
                    "source_evidence",
                ],
            ),
        ],
        ignore_index=True,
    )
    write_csv(missing, OUT / "data" / "field_missing_summary.csv")

    status_counts = cross["status"].value_counts().to_dict()
    stats = {
        "company_count": int(companies["stock_code"].nunique()),
        "subscription_rows": len(sub2),
        "snapshot_rows": len(snap2),
        "transfer_rows": len(tr2),
        "pass_count": int(status_counts.get("PASS", 0)),
        "info_count": int(status_counts.get("INFO", 0)),
        "review_count": int(status_counts.get("REVIEW", 0)),
    }

    week7_summary = pd.DataFrame(
        [
            {"metric": "统一样本公司数", "value": stats["company_count"], "note": "来自Week6 Final三表合并去重"},
            {"metric": "认缴/增资记录数", "value": stats["subscription_rows"], "note": "新增investor_type_final"},
            {"metric": "股权快照记录数", "value": stats["snapshot_rows"], "note": "新增investor_type_final"},
            {"metric": "股权转让记录数", "value": stats["transfer_rows"], "note": "新增转让方/受让方分类"},
            {"metric": "Cross-check PASS", "value": stats["pass_count"], "note": "可直接通过规则校验"},
            {"metric": "Cross-check INFO", "value": stats["info_count"], "note": "PDF未披露或需解释留空"},
            {"metric": "Cross-check REVIEW", "value": stats["review_count"], "note": "进入本周人工复核清单"},
        ]
    )
    write_csv(week7_summary, OUT / "data" / "week7_summary_stats.csv")

    dictionary = pd.DataFrame(
        [
            ["自然人", "姓名或auto分类为自然人/其他；且不含公司、合伙、基金、投资等机构关键词", "保留个人姓名，不强行判断是否为创始人", "孙国奉、曾烨"],
            ["员工持股平台", "名称包含员工持股、持股平台、员工平台等", "若仅为普通合伙企业但未披露员工属性，则放入其他投资平台", "员工持股平台/合伙企业"],
            ["控股股东/实际控制人", "证据或auto分类明确披露控股股东、实际控制人、创始人", "不能仅凭持股比例自动判断，需PDF证据", "实际控制人相关主体"],
            ["政府基金/国资平台", "名称含国资、政府、财政、引导基金、国有、高新投等", "如同时含创投，优先标政府/国资背景", "政府引导基金、国资平台"],
            ["VC", "名称含创业投资、创投、风险投资等早期投资关键词", "如同时为政府引导基金，标为政府基金/国资平台", "某某创业投资"],
            ["PE", "名称含私募、股权投资基金、投资基金、资本管理、资产管理等", "只做分类，不推断具体轮次", "某某股权投资基金"],
            ["产业资本/CVC/法人股东", "名称含公司、集团、实业、产业或auto为产业资本/法人股东", "公司型投资者不一定是CVC，保留CVC/法人股东并待复核", "深圳市云汉电子有限公司"],
            ["其他/待人工复核", "关键词不足或同一主体可能存在多重身份", "进入人工复核队列，后续以PDF和工商/基金备案信息确认", "一般合伙企业"],
        ],
        columns=["investor_type_final", "classification_rule", "boundary_note", "example"],
    )
    write_csv(dictionary, OUT / "data" / "investor_type_dictionary.csv")

    issues = []
    for i, row in cross[cross["status"].isin(["INFO", "REVIEW"])].reset_index(drop=True).iterrows():
        code = str(row.get("stock_code", "")).zfill(6) if not pd.isna(row.get("stock_code", "")) else ""
        company = companies.loc[companies["stock_code"] == code, "company_short"]
        issues.append(
            {
                "issue_id": f"W7-QA-{i+1:03d}",
                "stock_code": code,
                "company_short": company.iloc[0] if len(company) else "按check记录",
                "source": "cross_check",
                "issue_type": row.get("check_type", ""),
                "status": row.get("status", ""),
                "detail": row.get("detail", ""),
                "week7_action": "INFO保留说明；REVIEW进入PDF人工复核，不自动补值",
            }
        )
    for _, row in intra.iterrows():
        issues.append(
            {
                "issue_id": row.get("issue_id", ""),
                "stock_code": "",
                "company_short": row.get("company", ""),
                "source": "intra_group_review",
                "issue_type": "组内互查差异",
                "status": row.get("status", ""),
                "detail": row.get("difference", ""),
                "week7_action": row.get("resolution", ""),
            }
        )
    issues_df = pd.DataFrame(issues)
    write_csv(issues_df, OUT / "review" / "week7_issue_log.csv")
    write_csv(intra, OUT / "review" / "week7_intra_group_review.csv")
    write_csv(auto_vs_gold, OUT / "review" / "week7_auto_vs_gold_summary.csv")

    schema = """-- Week 7 PostgreSQL schema draft for PE/VC IPO prospectus three-table data
-- Author: Huo Hongkun
-- Principle: Final data keeps PDF-undisclosed numeric fields as NULL, not 0.

CREATE TABLE IF NOT EXISTS companies (
    stock_code TEXT PRIMARY KEY,
    company_short TEXT NOT NULL,
    market TEXT,
    week7_scope TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS investors (
    investor_id BIGSERIAL PRIMARY KEY,
    investor_name TEXT NOT NULL,
    investor_type_final TEXT,
    investor_type_method TEXT,
    investor_type_reason TEXT,
    UNIQUE (investor_name, investor_type_final)
);

CREATE TABLE IF NOT EXISTS subscription_events (
    record_id TEXT PRIMARY KEY,
    stock_code TEXT REFERENCES companies(stock_code),
    event_date TEXT,
    batch_label TEXT,
    subscriber_name TEXT,
    investor_type_final TEXT,
    subscription_shares_wan NUMERIC,
    subscription_amount_wan NUMERIC,
    subscription_price_yuan NUMERIC,
    computed_price_yuan NUMERIC,
    subscription_ratio_pct NUMERIC,
    currency TEXT,
    pdf_page TEXT,
    source_evidence TEXT,
    final_status TEXT,
    final_note TEXT
);

CREATE TABLE IF NOT EXISTS equity_snapshots (
    record_id TEXT PRIMARY KEY,
    stock_code TEXT REFERENCES companies(stock_code),
    time_point TEXT,
    equity_structure_scope TEXT,
    shareholder_name TEXT,
    investor_type_final TEXT,
    shares_held_wan NUMERIC,
    capital_contribution_wan NUMERIC,
    shareholding_ratio_pct NUMERIC,
    total_shares_wan NUMERIC,
    total_capital_wan NUMERIC,
    pdf_page TEXT,
    source_evidence TEXT,
    final_status TEXT,
    final_note TEXT
);

CREATE TABLE IF NOT EXISTS transfer_events (
    record_id TEXT PRIMARY KEY,
    stock_code TEXT REFERENCES companies(stock_code),
    transfer_date TEXT,
    batch_label TEXT,
    transferor_name TEXT,
    transferor_type_final TEXT,
    transferee_name TEXT,
    transferee_type_final TEXT,
    transferred_shares_wan NUMERIC,
    transfer_amount_wan NUMERIC,
    transfer_price_yuan NUMERIC,
    transfer_ratio_pct NUMERIC,
    pdf_page TEXT,
    source_evidence TEXT,
    final_status TEXT,
    final_note TEXT
);

CREATE TABLE IF NOT EXISTS validation_results (
    validation_id BIGSERIAL PRIMARY KEY,
    check_type TEXT,
    stock_code TEXT,
    record_id TEXT,
    status TEXT,
    metric NUMERIC,
    detail TEXT,
    week7_action TEXT
);
"""
    (OUT / "database" / "schema_postgresql.sql").write_text(schema, encoding="utf-8")

    import_plan = """# PostgreSQL导入计划

## 一、导入顺序

1. `companies_week7_manifest.csv` -> `companies`
2. `subscription_week7_final.csv` -> `subscription_events`
3. `equity_snapshot_week7_final.csv` -> `equity_snapshots`
4. `transfer_week7_final.csv` -> `transfer_events`
5. `week7_issue_log.csv` -> `validation_results`

## 二、注意事项

- 数值字段中的空值导入为 `NULL`，不替换为0。
- `stock_code` 按6位文本保存，避免 `001282` 被Excel或数据库转成 `1282`。
- `pdf_page` 保持文本格式，因为北交所招股书常见 `1-1-48` 这类页码。
- `source_evidence` 作为证据字段保留，后续可拆出独立证据表。
- 先做单机导入测试，再接入更大样本。

## 三、后续测试SQL

```sql
SELECT market, COUNT(DISTINCT stock_code) AS company_count
FROM companies
GROUP BY market;

SELECT investor_type_final, COUNT(*) AS records
FROM (
    SELECT investor_type_final FROM subscription_events
    UNION ALL
    SELECT investor_type_final FROM equity_snapshots
) t
GROUP BY investor_type_final
ORDER BY records DESC;

SELECT status, COUNT(*) AS records
FROM validation_results
GROUP BY status;
```
"""
    (OUT / "database" / "import_plan.md").write_text(import_plan, encoding="utf-8-sig")

    report_md = f"""# 第七周任务汇报：PE/VC 招股书三表数据治理与数据库化准备

姓名：霍泓锟  
日期：2026-08-01  
承接计划：数据质量复核、investor_type统一、组内互查差异整理、PostgreSQL表结构草案、周报提交。

## 一、本周完成内容

本周工作重点从“继续抽取更多文件”转向“让已有8家公司数据更可信、更可追溯、更容易进入后续研究”。我使用第六周形成的Final三表作为基础，生成Week7版数据，并新增投资主体分类字段和问题复核记录。

本周完成的主要材料包括：

- `data/subscription_week7_final.csv`：认缴/增资表，新增 `investor_type_final`。
- `data/equity_snapshot_week7_final.csv`：股权快照表，新增 `investor_type_final`。
- `data/transfer_week7_final.csv`：股权转让表，新增转让方/受让方分类字段。
- `data/investor_type_dictionary.csv`：投资主体分类口径说明。
- `review/week7_issue_log.csv`：本周质量复核和互查差异记录。
- `database/schema_postgresql.sql`：PostgreSQL初步表结构。
- `database/import_plan.md`：后续数据库导入顺序和注意事项。

## 二、样本和记录概况

| 指标 | 数值 | 说明 |
|---|---:|---|
| 统一样本公司数 | {stats['company_count']} | 来自第六周统一8家公司样本 |
| 认缴/增资记录 | {stats['subscription_rows']} | 主要用于刻画融资/出资流量 |
| 股权快照记录 | {stats['snapshot_rows']} | 主要用于刻画某一时点股权结构 |
| 股权转让记录 | {stats['transfer_rows']} | 数量少，但误命中风险较高 |
| Cross-check PASS | {stats['pass_count']} | 规则校验通过 |
| Cross-check INFO | {stats['info_count']} | PDF未披露或需要解释留空 |
| Cross-check REVIEW | {stats['review_count']} | 需要回到PDF人工复核 |

## 三、investor_type统一口径

老师之前反复强调“不同类别分别处理”，因此本周把投资主体分类作为优先任务。分类口径不是简单地把所有机构都归为PE/VC，而是区分自然人、员工持股平台、控股股东/实际控制人、政府基金/国资平台、VC、PE、产业资本/CVC/法人股东和其他/待人工复核。

当前结果中，很多记录仍然来自自然人或一般法人股东，这说明招股书历史沿革三表并不等同于纯PE/VC数据库。后续做研究时，应当先筛选出真正的VC/PE/政府基金/产业资本样本，再分别讨论其进入时点、持股比例和退出方式。

## 四、本周质量复核发现

本周没有把缺失字段强行补齐，而是把缺失原因记录下来。主要问题包括：

1. 部分认缴记录只披露出资额或注册资本，没有披露股份数和单价，Final保留空值。
2. 赛分科技存在股权快照比例合计异常项，需要回到PDF确认是否把多个时点或多个口径合并计算。
3. 黄山谷捷若干快照节点没有可求和比例，需要人工复核原表是否未披露比例。
4. 股权转让事件数量少，但Auto误命中风险较高，必须逐条保留证据句和页码。
5. `stock_code`、`pdf_page` 等字段必须保留文本格式，避免数据库和Excel自动转型造成信息损失。

## 五、数据库化准备

本周建立了PostgreSQL表结构草案，包含公司表、投资主体表、认缴事件表、股权快照表、股权转让表和验证结果表。表结构设计坚持两个原则：

- 第一，事件表与证据字段绑定，后续每个数字都能回到PDF页码和原文片段。
- 第二，空值保留为数据库 `NULL`，表示“PDF未披露/暂未识别”，不把空值处理成0。

## 六、与论文研读和后续研究的衔接

前期论文研读提醒我，PE/VC研究不能停留在“抓到了多少表”，而要进一步问：资本进入企业之后是否影响企业治理、创新、IPO表现或股权结构稳定性。本周的数据治理工作就是为后续研究做准备。只有先把投资主体类型、进入时点、持股比例和证据来源整理清楚，后续才能提出可检验问题。

## 七、下一步计划

下一周建议优先完成：

1. 按 `database/import_plan.md` 把Week7 CSV真实导入PostgreSQL。
2. 对 `review/week7_issue_log.csv` 中的REVIEW项逐条回到PDF人工核对。
3. 将 `investor_type_final` 与基金备案编码、GP/LP结构继续连接，优先处理PE/VC和政府基金。
4. 基于数据库输出第一版描述性统计，例如不同板块投资主体类型分布、三表字段缺失率、转让事件数量等。
5. 形成一个小研究问题：不同类型投资主体在上市前进入阶段和持股比例上是否存在差异。
"""
    (OUT / "report" / "week7_report.md").write_text(report_md, encoding="utf-8-sig")

    readme = """# 霍泓锟 第七周任务提交

本文件夹承接前六周PE/VC招股书结构化抽取项目，重点完成第七周的数据质量复核、投资主体分类统一、组内互查差异整理和PostgreSQL数据库化准备。

## 目录说明

| 目录 | 内容 |
|---|---|
| `data/` | Week7版三表、公司清单、分类字典、缺失统计和汇总统计 |
| `review/` | 组内互查差异、Auto-vs-Gold摘要、本周问题记录 |
| `database/` | PostgreSQL建表SQL、导入计划和本机psql版本检查记录 |
| `report/` | 第七周汇报Markdown和Word版报告 |
| `tables/` | 第七周Excel汇总工作簿 |
| `scripts/` | 生成本提交包的可复现脚本 |
| `literature/` | 前期论文研读材料副本，用于说明研究问题衔接 |

## 运行方式

```bash
python scripts/build_week7_submission.py
node scripts/build_week7_workbook.mjs
```

## 核心原则

- Auto结果必须来自PDF或Markdown，不读取Gold/Final主体和页码。
- Final允许人工修订，但保留修改原因和PDF证据。
- PDF未披露的金额、比例、单价等字段保留空值，不写0。
- `investor_type_final` 只是统一口径的第一版，复杂主体仍需基金备案、GP/LP或工商信息辅助确认。
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8-sig")
    (OUT / "requirements.txt").write_text("pandas\npython-docx\n", encoding="utf-8")

    import_test_record = """# PostgreSQL导入测试记录

姓名：霍泓锟  
日期：2026-08-01

## 一、本机环境检查

已在本机发现 PostgreSQL 命令行工具：

```text
C:\\Program Files\\PostgreSQL\\18\\bin\\psql.exe
psql (PostgreSQL) 18.4
```

## 二、本周完成情况

本周已完成数据库化前的表结构准备：

- `schema_postgresql.sql`：公司表、投资主体表、认缴事件表、股权快照表、股权转让表、验证结果表。
- `import_plan.md`：导入顺序、字段注意事项和测试SQL。
- `data/*.csv`：可导入数据库的 Week7 版三表与辅助表。

## 三、尚未直接导入的原因

当前任务环境中没有明确的 PostgreSQL 用户名、密码和目标数据库名。为避免在未授权数据库中创建表，本周先完成可复现表结构和导入说明。后续拿到数据库连接信息后，可按以下顺序执行。

## 四、后续导入命令示例

```powershell
& "C:\\Program Files\\PostgreSQL\\18\\bin\\psql.exe" -U postgres -d pevc_week7 -f "database/schema_postgresql.sql"
```

导入 CSV 时需注意：

- `stock_code` 使用文本字段，避免 `001282` 变成 `1282`。
- 空值导入为 `NULL`，不能替换为 0。
- `pdf_page` 使用文本字段，兼容 `1-1-48` 这类页码。
"""
    (OUT / "database" / "import_test_record.md").write_text(import_test_record, encoding="utf-8-sig")

    # Keep the literature review from the prior Week 7 work as a source appendix.
    lit_dir = OUT / "literature"
    lit_dir.mkdir(exist_ok=True)
    if OLD_WEEK7:
        for item in OLD_WEEK7.iterdir():
            if item.is_file():
                shutil.copy2(item, lit_dir / item.name)

    build_docx(OUT / "report" / "第七周任务汇报_霍泓锟.docx", stats, issues, type_stats)

    # Compact source manifest for reproducibility.
    source_manifest = pd.DataFrame(
        [
            ["Week6 Final认缴表", str(WEEK6 / "final" / "subscription_final.csv")],
            ["Week6 Final股权快照表", str(WEEK6 / "final" / "equity_snapshot_final.csv")],
            ["Week6 Final股权转让表", str(WEEK6 / "final" / "transfer_final.csv")],
            ["Week6 cross-check", str(WEEK6 / "validation" / "cross_check.csv")],
            ["Week6 Auto-vs-Gold", str(WEEK6 / "validation" / "auto_vs_gold.csv")],
            ["Week6组内互查", str(WEEK6 / "review" / "intra_group_review.csv")],
            ["Week7论文研读材料", str(OLD_WEEK7) if OLD_WEEK7 else ""],
        ],
        columns=["source_name", "source_path"],
    )
    write_csv(source_manifest, OUT / "data" / "source_manifest.csv")

    workbook_payload = {
        "summary": week7_summary.to_dict(orient="records"),
        "company_records": company_stats_df.to_dict(orient="records"),
        "investor_type_stats": type_stats.to_dict(orient="records"),
        "investor_type_dictionary": dictionary.to_dict(orient="records"),
        "missing_summary": missing.to_dict(orient="records"),
        "issue_log": issues_df.head(80).to_dict(orient="records"),
        "auto_vs_gold": auto_vs_gold.to_dict(orient="records"),
    }
    (OUT / "tables" / "week7_workbook_data.json").write_text(
        json.dumps(workbook_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
