"""Week 8 PE/VC prospectus data quality and research-prep pipeline.

This script uses only Python standard libraries. It reads the Week 7
three-table Final CSV files, normalizes stock codes, creates quality checks,
and writes Week 8 derived tables used by the report and workbook.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "input_week7"
DERIVED = ROOT / "data" / "derived"
OUTPUTS = ROOT / "outputs"
REVIEW = ROOT / "review"
DATABASE = ROOT / "database"
LOGS = ROOT / "logs"


COMPANIES = {
    "001282": ("三联锻造", "主板"),
    "603418": ("友升股份", "主板"),
    "301563": ("云汉芯城", "创业板"),
    "301581": ("黄山谷捷", "创业板"),
    "688758": ("赛分科技", "科创板"),
    "688775": ("影石创新", "科创板"),
    "920100": ("三协电机", "北交所"),
    "920116": ("星图测控", "北交所"),
}

SHORT_TO_CODE = {short: code for code, (short, _market) in COMPANIES.items()}

BROAD_PEVC_TYPES = {
    "VC",
    "PE",
    "政府基金/国资平台",
    "产业资本/CVC/法人股东",
    "其他投资平台",
}

MISSING_FIELD_PLAN = {
    "subscription": [
        "subscriber_name",
        "investor_type_final",
        "subscription_shares_wan",
        "subscription_amount_wan",
        "subscription_price_yuan",
        "subscription_ratio_pct",
        "pdf_page",
        "source_evidence",
    ],
    "equity_snapshot": [
        "shareholder_name",
        "investor_type_final",
        "shares_held_wan",
        "capital_contribution_wan",
        "shareholding_ratio_pct",
        "total_shares_wan",
        "total_capital_wan",
        "pdf_page",
        "source_evidence",
    ],
    "transfer": [
        "transferor_name",
        "transferee_name",
        "transferor_type_final",
        "transferee_type_final",
        "transferred_shares_wan",
        "transfer_amount_wan",
        "transfer_price_yuan",
        "transfer_ratio_pct",
        "pdf_page",
        "source_evidence",
    ],
}


def ensure_dirs() -> None:
    for folder in [DERIVED, OUTPUTS, REVIEW, DATABASE, LOGS]:
        folder.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    last_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8-sig", "gb18030", "utf-16"):
        try:
            with path.open("r", encoding=encoding, newline="") as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError as exc:
            last_error = exc
    raise UnicodeDecodeError(
        last_error.encoding if last_error else "unknown",
        last_error.object if last_error else b"",
        last_error.start if last_error else 0,
        last_error.end if last_error else 0,
        f"Cannot decode {path} with utf-8-sig, gb18030, or utf-16.",
    )


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        seen = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    keys.append(key)
                    seen.add(key)
        fieldnames = keys
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def nonempty(value: object) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return text not in {"", "nan", "NaN", "None", "null"}


def to_float(value: object) -> float | None:
    if not nonempty(value):
        return None
    text = str(value).strip()
    text = text.replace(",", "").replace("%", "").replace("，", "")
    try:
        val = float(text)
    except ValueError:
        return None
    if math.isnan(val):
        return None
    return val


def norm_pct(value: object) -> float | None:
    return to_float(value)


def normalize_stock_code(row: dict[str, str]) -> str:
    short = (row.get("company_short") or "").strip()
    if short in SHORT_TO_CODE:
        return SHORT_TO_CODE[short]
    raw = str(row.get("stock_code") or "").strip()
    raw = raw.split(".")[0] if raw.endswith(".0") else raw
    if raw.isdigit() and len(raw) < 6:
        return raw.zfill(6)
    return raw


def normalize_rows(rows: list[dict[str, str]], table_name: str) -> list[dict[str, str]]:
    output = []
    for row in rows:
        clean = dict(row)
        code = normalize_stock_code(clean)
        short = clean.get("company_short") or COMPANIES.get(code, ("", ""))[0]
        market = COMPANIES.get(code, ("", "未识别"))[1]
        clean["stock_code"] = code
        clean["company_short"] = short
        clean["market"] = market
        clean["source_table"] = table_name
        output.append(clean)
    return output


def pct(num: float, den: float) -> float:
    if den == 0:
        return 0.0
    return round(num / den, 4)


def build_company_summary(subscription: list[dict], snapshot: list[dict], transfer: list[dict]) -> list[dict]:
    records = []
    for code, (short, market) in COMPANIES.items():
        sub = [r for r in subscription if r["stock_code"] == code]
        snap = [r for r in snapshot if r["stock_code"] == code]
        tr = [r for r in transfer if r["stock_code"] == code]
        all_rows = sub + snap + tr
        broad = [
            r
            for r in sub + snap
            if (r.get("investor_type_final") or r.get("investor_type_auto") or "").strip()
            in BROAD_PEVC_TYPES
        ]
        records.append(
            {
                "stock_code": code,
                "company_short": short,
                "market": market,
                "subscription_records": len(sub),
                "snapshot_records": len(snap),
                "transfer_records": len(tr),
                "total_records": len(all_rows),
                "broad_pevc_records": len(broad),
                "pdf_page_coverage": round(
                    pct(sum(1 for r in all_rows if nonempty(r.get("pdf_page"))), len(all_rows)) * 100,
                    2,
                ),
                "evidence_coverage": round(
                    pct(sum(1 for r in all_rows if nonempty(r.get("source_evidence"))), len(all_rows)) * 100,
                    2,
                ),
            }
        )
    return records


def build_investor_type_stats(subscription: list[dict], snapshot: list[dict]) -> list[dict]:
    counter: Counter[str] = Counter()
    for row in subscription + snapshot:
        investor_type = (row.get("investor_type_final") or row.get("investor_type_auto") or "未分类").strip()
        counter[investor_type or "未分类"] += 1
    total = sum(counter.values())
    return [
        {
            "investor_type_final": key,
            "record_count": count,
            "share": round(pct(count, total) * 100, 2),
        }
        for key, count in counter.most_common()
    ]


def build_transfer_party_stats(transfer: list[dict]) -> list[dict]:
    counter: Counter[tuple[str, str]] = Counter()
    for row in transfer:
        counter[("transferor", row.get("transferor_type_final") or "未分类")] += 1
        counter[("transferee", row.get("transferee_type_final") or "未分类")] += 1
    total = sum(counter.values())
    rows = []
    for (party_role, investor_type), count in sorted(counter.items()):
        rows.append(
            {
                "party_role": party_role,
                "investor_type_final": investor_type,
                "party_count": count,
                "share": round(pct(count, total) * 100, 2),
            }
        )
    return rows


def build_missing_summary(tables: dict[str, list[dict]]) -> list[dict]:
    rows = []
    for table_name, data in tables.items():
        total = len(data)
        for field in MISSING_FIELD_PLAN[table_name]:
            missing = sum(1 for r in data if not nonempty(r.get(field)))
            rows.append(
                {
                    "table_name": table_name,
                    "field": field,
                    "records": total,
                    "missing_count": missing,
                    "missing_rate": round(pct(missing, total) * 100, 2),
                    "week8_principle": "PDF未披露留空；不把空值改写为0",
                }
            )
    return sorted(rows, key=lambda r: (-float(r["missing_rate"]), r["table_name"], r["field"]))


def check_snapshot_ratio(snapshot: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in snapshot:
        key = (row["stock_code"], row["company_short"], row.get("time_point", ""))
        grouped[key].append(row)

    rows = []
    for (code, short, time_point), items in sorted(grouped.items()):
        values = [norm_pct(r.get("shareholding_ratio_pct")) for r in items]
        values = [v for v in values if v is not None]
        ratio_sum = round(sum(values), 4) if values else None
        if not values:
            status = "REVIEW"
            note = "该时点无可求和持股比例，需要回到PDF判断是否原文未披露。"
        elif 98 <= ratio_sum <= 102:
            status = "PASS"
            note = "比例合计接近100%，可作为结构化结果使用。"
        elif 95 <= ratio_sum <= 105:
            status = "INFO"
            note = "比例合计略偏离100%，通常由四舍五入或部分股东口径导致。"
        else:
            status = "REVIEW"
            note = "比例合计明显异常，优先进入人工复核。"
        rows.append(
            {
                "check_id": f"SNAP-{code}-{len(rows) + 1:03d}",
                "stock_code": code,
                "company_short": short,
                "time_point": time_point,
                "row_count": len(items),
                "ratio_observed_rows": len(values),
                "ratio_sum_pct": "" if ratio_sum is None else ratio_sum,
                "status": status,
                "note": note,
            }
        )
    return rows


def check_subscription_price(subscription: list[dict]) -> list[dict]:
    rows = []
    for i, row in enumerate(subscription, start=1):
        amount = to_float(row.get("subscription_amount_wan"))
        shares = to_float(row.get("subscription_shares_wan"))
        disclosed = to_float(row.get("subscription_price_yuan"))
        computed = round(amount / shares, 4) if amount is not None and shares not in (None, 0) else None
        if disclosed is not None and computed is not None:
            diff = round(abs(disclosed - computed), 4)
            status = "PASS" if diff <= 0.02 else "REVIEW"
            note = "披露单价与金额/股份数计算值一致。" if status == "PASS" else "披露单价与计算值差异较大，可能存在单位口径问题。"
        elif disclosed is None and computed is not None:
            diff = ""
            status = "INFO"
            note = "PDF未直接披露单价，脚本仅生成可复核计算值。"
        else:
            diff = ""
            status = "INFO"
            note = "金额或股份数未披露，单价不计算。"
        rows.append(
            {
                "check_id": f"SUB-{row['stock_code']}-{i:03d}",
                "record_id": row.get("record_id"),
                "stock_code": row["stock_code"],
                "company_short": row["company_short"],
                "subscriber_name": row.get("subscriber_name"),
                "subscription_amount_wan": row.get("subscription_amount_wan"),
                "subscription_shares_wan": row.get("subscription_shares_wan"),
                "disclosed_price_yuan": row.get("subscription_price_yuan"),
                "computed_price_yuan": "" if computed is None else computed,
                "abs_diff": diff,
                "status": status,
                "note": note,
            }
        )
    return rows


def check_transfer_events(transfer: list[dict]) -> list[dict]:
    rows = []
    for i, row in enumerate(transfer, start=1):
        issues = []
        if not nonempty(row.get("transfer_amount_wan")) and not nonempty(row.get("transfer_price_yuan")):
            issues.append("金额和单价均未披露")
        if not nonempty(row.get("transferred_shares_wan")) and not nonempty(row.get("transfer_ratio_pct")):
            issues.append("数量和比例均未披露")
        if not nonempty(row.get("pdf_page")) or not nonempty(row.get("source_evidence")):
            issues.append("页码或证据缺失")

        if "页码或证据缺失" in issues:
            status = "REVIEW"
        elif issues:
            status = "INFO"
        else:
            status = "PASS"

        rows.append(
            {
                "check_id": f"TR-{row['stock_code']}-{i:03d}",
                "record_id": row.get("record_id"),
                "stock_code": row["stock_code"],
                "company_short": row["company_short"],
                "transferor_name": row.get("transferor_name"),
                "transferee_name": row.get("transferee_name"),
                "status": status,
                "issue_note": "；".join(issues) if issues else "核心字段与证据齐全",
                "week8_action": "未披露字段保留空值；若缺少证据则回PDF复核",
            }
        )
    return rows


def build_review_queue(
    week7_issues: list[dict],
    snapshot_checks: list[dict],
    subscription_checks: list[dict],
    transfer_checks: list[dict],
) -> list[dict]:
    rows = []
    for item in week7_issues:
        status = (item.get("status") or "").strip()
        if status in {"REVIEW", "已记录"}:
            rows.append(
                {
                    "queue_id": f"W8-W7-{len(rows) + 1:03d}",
                    "stock_code": normalize_stock_code(item),
                    "company_short": item.get("company_short"),
                    "source": "week7_issue_log",
                    "issue_type": item.get("issue_type"),
                    "status": "P1-人工复核" if status == "REVIEW" else "P2-保留记录",
                    "detail": item.get("detail"),
                    "suggested_action": "回到PDF页码或证据段核验；确认为未披露时继续留空。",
                }
            )
    for item in snapshot_checks:
        if item["status"] == "REVIEW":
            rows.append(
                {
                    "queue_id": f"W8-SNAP-{len(rows) + 1:03d}",
                    "stock_code": item["stock_code"],
                    "company_short": item["company_short"],
                    "source": "snapshot_ratio_check",
                    "issue_type": "snapshot_ratio_sum",
                    "status": "P1-人工复核",
                    "detail": f"{item['time_point']}：比例合计={item['ratio_sum_pct']}",
                    "suggested_action": item["note"],
                }
            )
    for item in subscription_checks:
        if item["status"] == "REVIEW":
            rows.append(
                {
                    "queue_id": f"W8-SUB-{len(rows) + 1:03d}",
                    "stock_code": item["stock_code"],
                    "company_short": item["company_short"],
                    "source": "subscription_price_check",
                    "issue_type": "subscription_price",
                    "status": "P1-人工复核",
                    "detail": f"{item['subscriber_name']}：披露价={item['disclosed_price_yuan']}，计算价={item['computed_price_yuan']}",
                    "suggested_action": item["note"],
                }
            )
    for item in transfer_checks:
        if item["status"] == "REVIEW":
            rows.append(
                {
                    "queue_id": f"W8-TR-{len(rows) + 1:03d}",
                    "stock_code": item["stock_code"],
                    "company_short": item["company_short"],
                    "source": "transfer_event_check",
                    "issue_type": "transfer_evidence",
                    "status": "P1-人工复核",
                    "detail": item["issue_note"],
                    "suggested_action": item["week8_action"],
                }
            )
    return rows


def build_quality_metrics(
    tables: dict[str, list[dict]],
    review_queue: list[dict],
) -> list[dict]:
    review_by_table = Counter()
    for item in review_queue:
        source = item.get("source", "")
        if source.startswith("snapshot"):
            review_by_table["equity_snapshot"] += 1
        elif source.startswith("subscription"):
            review_by_table["subscription"] += 1
        elif source.startswith("transfer"):
            review_by_table["transfer"] += 1
        else:
            review_by_table["cross_table"] += 1

    rows = []
    for table_name, data in tables.items():
        total = len(data)
        pdf_ok = sum(1 for r in data if nonempty(r.get("pdf_page")))
        evidence_ok = sum(1 for r in data if nonempty(r.get("source_evidence")))
        type_field = "investor_type_final"
        if table_name == "transfer":
            type_ok = sum(
                1
                for r in data
                if nonempty(r.get("transferor_type_final")) and nonempty(r.get("transferee_type_final"))
            )
        else:
            type_ok = sum(1 for r in data if nonempty(r.get(type_field)))
        rows.append(
            {
                "table_name": table_name,
                "total_records": total,
                "pdf_page_coverage": round(pct(pdf_ok, total) * 100, 2),
                "evidence_coverage": round(pct(evidence_ok, total) * 100, 2),
                "investor_type_coverage": round(pct(type_ok, total) * 100, 2),
                "review_queue_items": review_by_table[table_name],
                "quality_note": "已具备描述性统计基础；REVIEW项需人工回PDF确认。",
            }
        )
    rows.append(
        {
            "table_name": "cross_table",
            "total_records": sum(len(v) for v in tables.values()),
            "pdf_page_coverage": "",
            "evidence_coverage": "",
            "investor_type_coverage": "",
            "review_queue_items": review_by_table["cross_table"],
            "quality_note": "来自组内互查与跨表口径差异，保留为问题追踪项。",
        }
    )
    return rows


def build_board_stats(company_summary: list[dict]) -> list[dict]:
    grouped: dict[str, dict] = {}
    for row in company_summary:
        market = row["market"]
        target = grouped.setdefault(
            market,
            {
                "market": market,
                "company_count": 0,
                "subscription_records": 0,
                "snapshot_records": 0,
                "transfer_records": 0,
                "total_records": 0,
                "broad_pevc_records": 0,
            },
        )
        target["company_count"] += 1
        for key in [
            "subscription_records",
            "snapshot_records",
            "transfer_records",
            "total_records",
            "broad_pevc_records",
        ]:
            target[key] += int(row[key])
    for row in grouped.values():
        row["broad_pevc_record_share"] = round(pct(row["broad_pevc_records"], row["total_records"]) * 100, 2)
    return sorted(grouped.values(), key=lambda r: r["market"])


def build_research_variables(
    subscription: list[dict],
    snapshot: list[dict],
    transfer: list[dict],
    review_queue: list[dict],
) -> list[dict]:
    review_counter = Counter(item["stock_code"] for item in review_queue if nonempty(item.get("stock_code")))
    rows = []
    for code, (short, market) in COMPANIES.items():
        sub = [r for r in subscription if r["stock_code"] == code]
        snap = [r for r in snapshot if r["stock_code"] == code]
        tr = [r for r in transfer if r["stock_code"] == code]
        investor_types = [
            (r.get("investor_type_final") or r.get("investor_type_auto") or "未分类").strip()
            for r in sub + snap
        ]
        counts = Counter(investor_types)
        broad = sum(counts[t] for t in BROAD_PEVC_TYPES)
        total = len(sub) + len(snap)
        rows.append(
            {
                "stock_code": code,
                "company_short": short,
                "market": market,
                "has_vc_or_pe": int(counts["VC"] + counts["PE"] > 0),
                "vc_record_count": counts["VC"],
                "pe_record_count": counts["PE"],
                "broad_pevc_record_count": broad,
                "broad_pevc_record_share": round(pct(broad, total) * 100, 2),
                "natural_person_record_share": round(pct(counts["自然人"], total) * 100, 2),
                "distinct_investor_type_count": len(set(investor_types)) if investor_types else 0,
                "transfer_event_count": len(tr),
                "p1_review_item_count": review_counter[code],
                "research_use_note": "可用于描述性统计；正式回归前需扩大样本并人工复核P1项。",
            }
        )
    return rows


def build_task_status() -> list[dict]:
    return [
        {
            "week8_task": "完善8家公司三表数据质量",
            "status": "已完成基础审计",
            "evidence_file": "data/derived/quality_metrics_week8.csv",
            "remaining_work": "P1问题仍需回PDF人工核验。",
        },
        {
            "week8_task": "统一investor_type分类口径",
            "status": "已完成统计与覆盖率检查",
            "evidence_file": "data/derived/investor_type_stats_week8.csv",
            "remaining_work": "复杂基金仍需备案编码、GP/LP结构辅助确认。",
        },
        {
            "week8_task": "整理组内互查差异",
            "status": "已转入问题队列",
            "evidence_file": "review/week8_review_queue.csv",
            "remaining_work": "下一周逐条标注处理结果。",
        },
        {
            "week8_task": "建立PostgreSQL初步表结构",
            "status": "已扩展schema和导入脚本",
            "evidence_file": "database/schema_postgresql_week8.sql",
            "remaining_work": "拿到数据库连接信息后执行全量导入。",
        },
        {
            "week8_task": "补充本周短报告",
            "status": "已完成",
            "evidence_file": "report/霍泓锟_第八周任务报告.pdf",
            "remaining_work": "报告可继续根据老师反馈补充PDF原文页码截图。",
        },
    ]


def write_database_files() -> None:
    schema = """-- Week 8 PostgreSQL schema extension for PE/VC prospectus data
-- Author: Huo Hongkun
-- Principle: PDF-undisclosed values remain NULL, not 0.

CREATE TABLE IF NOT EXISTS week8_company_summary (
    stock_code TEXT PRIMARY KEY,
    company_short TEXT NOT NULL,
    market TEXT,
    subscription_records INTEGER,
    snapshot_records INTEGER,
    transfer_records INTEGER,
    total_records INTEGER,
    broad_pevc_records INTEGER,
    pdf_page_coverage NUMERIC,
    evidence_coverage NUMERIC
);

CREATE TABLE IF NOT EXISTS week8_quality_metrics (
    table_name TEXT PRIMARY KEY,
    total_records INTEGER,
    pdf_page_coverage NUMERIC,
    evidence_coverage NUMERIC,
    investor_type_coverage NUMERIC,
    review_queue_items INTEGER,
    quality_note TEXT
);

CREATE TABLE IF NOT EXISTS week8_review_queue (
    queue_id TEXT PRIMARY KEY,
    stock_code TEXT,
    company_short TEXT,
    source TEXT,
    issue_type TEXT,
    status TEXT,
    detail TEXT,
    suggested_action TEXT
);

CREATE TABLE IF NOT EXISTS week8_research_variables (
    stock_code TEXT PRIMARY KEY,
    company_short TEXT,
    market TEXT,
    has_vc_or_pe INTEGER,
    vc_record_count INTEGER,
    pe_record_count INTEGER,
    broad_pevc_record_count INTEGER,
    broad_pevc_record_share NUMERIC,
    natural_person_record_share NUMERIC,
    distinct_investor_type_count INTEGER,
    transfer_event_count INTEGER,
    p1_review_item_count INTEGER,
    research_use_note TEXT
);
"""
    import_sql = """-- Run from the Week 8 submission root folder in psql.
-- Example:
-- psql -d pevc -f database/schema_postgresql_week8.sql
-- psql -d pevc -f database/import_week8_derived_tables.sql

\\copy week8_company_summary FROM 'data/derived/company_summary_week8.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\\copy week8_quality_metrics FROM 'data/derived/quality_metrics_week8.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\\copy week8_review_queue FROM 'review/week8_review_queue.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\\copy week8_research_variables FROM 'data/derived/research_variables_week8.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
"""
    (DATABASE / "schema_postgresql_week8.sql").write_text(schema, encoding="utf-8")
    (DATABASE / "import_week8_derived_tables.sql").write_text(import_sql, encoding="utf-8")


def write_summary_md(summary: dict[str, object]) -> None:
    lines = [
        "# 第八周任务自动生成摘要",
        "",
        f"运行时间：{summary['run_time']}",
        "",
        "## 核心数字",
        "",
        f"- 样本公司：{summary['company_count']} 家",
        f"- 认缴/增资记录：{summary['subscription_records']} 条",
        f"- 股权快照记录：{summary['snapshot_records']} 条",
        f"- 股权转让记录：{summary['transfer_records']} 条",
        f"- 广义PE/VC相关记录：{summary['broad_pevc_records']} 条",
        f"- P1人工复核项：{summary['p1_review_items']} 条",
        "",
        "## 本周判断",
        "",
        "第八周的核心不再是继续堆文件，而是把第七周已经形成的三表数据转化为可审计、可入库、可做描述性统计的研究准备数据。脚本已经完成证券代码修正、字段缺失率统计、投资主体类型统计、快照比例校验、认缴单价校验和转让事件证据检查。",
        "",
        "## 工程原则",
        "",
        "PDF未披露的金额、比例、单价继续留空，不以0替代；Auto结果和人工Final结果分开保存；所有需要人工判断的问题进入review队列。",
    ]
    (OUTPUTS / "week8_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_manifest() -> list[dict[str, str]]:
    files = [
        ("README.md", "提交说明和运行方法"),
        ("code/week8_data_quality_pipeline.py", "第八周数据质量主流程"),
        ("code/build_week8_report_pdf.py", "报告PDF生成脚本"),
        ("code/build_week8_workbook.mjs", "Excel汇总工作簿生成脚本"),
        ("data/input_week7/subscription_week7_final.csv", "第七周认缴/增资Final输入"),
        ("data/input_week7/equity_snapshot_week7_final.csv", "第七周股权快照Final输入"),
        ("data/input_week7/transfer_week7_final.csv", "第七周股权转让Final输入"),
        ("data/derived/subscription_week8_clean.csv", "第八周清洗后认缴表"),
        ("data/derived/equity_snapshot_week8_clean.csv", "第八周清洗后股权快照表"),
        ("data/derived/transfer_week8_clean.csv", "第八周清洗后股权转让表"),
        ("data/derived/company_summary_week8.csv", "公司层面记录统计"),
        ("data/derived/investor_type_stats_week8.csv", "投资主体类型统计"),
        ("data/derived/field_missing_summary_week8.csv", "字段缺失率统计"),
        ("data/derived/research_variables_week8.csv", "下一阶段研究变量草案"),
        ("review/week8_review_queue.csv", "人工复核问题队列"),
        ("database/schema_postgresql_week8.sql", "PostgreSQL扩展表结构"),
        ("database/import_week8_derived_tables.sql", "PostgreSQL导入脚本"),
        ("outputs/week8_summary.md", "自动生成摘要"),
        ("outputs/week8_workbook_data.json", "Excel工作簿输入数据"),
        ("report/霍泓锟_第八周任务报告.pdf", "第八周报告PDF"),
        ("report/week8_report.md", "第八周报告Markdown"),
        ("outputs/week8_summary_workbook.xlsx", "第八周Excel汇总工作簿"),
    ]
    return [
        {
            "relative_path": rel,
            "purpose": purpose,
            "exists_after_pipeline": str((ROOT / rel).exists()),
        }
        for rel, purpose in files
    ]


def main() -> None:
    ensure_dirs()
    if "--manifest-only" in sys.argv:
        manifest = build_manifest()
        write_csv(DERIVED / "week8_submission_manifest.csv", manifest)
        print("Manifest refreshed.")
        return

    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    subscription = normalize_rows(read_csv(INPUT / "subscription_week7_final.csv"), "subscription")
    snapshot = normalize_rows(read_csv(INPUT / "equity_snapshot_week7_final.csv"), "equity_snapshot")
    transfer = normalize_rows(read_csv(INPUT / "transfer_week7_final.csv"), "transfer")
    week7_issues = read_csv(REVIEW / "week7_issue_log.csv")

    tables = {"subscription": subscription, "equity_snapshot": snapshot, "transfer": transfer}

    write_csv(DERIVED / "subscription_week8_clean.csv", subscription)
    write_csv(DERIVED / "equity_snapshot_week8_clean.csv", snapshot)
    write_csv(DERIVED / "transfer_week8_clean.csv", transfer)

    company_summary = build_company_summary(subscription, snapshot, transfer)
    investor_type_stats = build_investor_type_stats(subscription, snapshot)
    transfer_party_stats = build_transfer_party_stats(transfer)
    missing_summary = build_missing_summary(tables)
    snapshot_checks = check_snapshot_ratio(snapshot)
    subscription_checks = check_subscription_price(subscription)
    transfer_checks = check_transfer_events(transfer)
    review_queue = build_review_queue(week7_issues, snapshot_checks, subscription_checks, transfer_checks)
    quality_metrics = build_quality_metrics(tables, review_queue)
    board_stats = build_board_stats(company_summary)
    research_variables = build_research_variables(subscription, snapshot, transfer, review_queue)
    task_status = build_task_status()

    write_csv(DERIVED / "company_summary_week8.csv", company_summary)
    write_csv(DERIVED / "investor_type_stats_week8.csv", investor_type_stats)
    write_csv(DERIVED / "transfer_party_stats_week8.csv", transfer_party_stats)
    write_csv(DERIVED / "field_missing_summary_week8.csv", missing_summary)
    write_csv(DERIVED / "snapshot_ratio_check_week8.csv", snapshot_checks)
    write_csv(DERIVED / "subscription_price_check_week8.csv", subscription_checks)
    write_csv(DERIVED / "transfer_event_check_week8.csv", transfer_checks)
    write_csv(REVIEW / "week8_review_queue.csv", review_queue)
    write_csv(DERIVED / "quality_metrics_week8.csv", quality_metrics)
    write_csv(DERIVED / "board_stats_week8.csv", board_stats)
    write_csv(DERIVED / "research_variables_week8.csv", research_variables)
    write_csv(DERIVED / "week8_task_status.csv", task_status)
    write_database_files()

    broad_pevc_records = sum(int(r["broad_pevc_records"]) for r in company_summary)
    p1_review_items = sum(1 for r in review_queue if str(r.get("status", "")).startswith("P1"))
    summary = {
        "run_time": run_time,
        "company_count": len(COMPANIES),
        "subscription_records": len(subscription),
        "snapshot_records": len(snapshot),
        "transfer_records": len(transfer),
        "broad_pevc_records": broad_pevc_records,
        "p1_review_items": p1_review_items,
    }
    (OUTPUTS / "week8_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    workbook_payload = {
        "summary": summary,
        "task_status": task_status,
        "company_summary": company_summary,
        "quality_metrics": quality_metrics,
        "investor_type_stats": investor_type_stats,
        "transfer_party_stats": transfer_party_stats,
        "missing_summary_top": missing_summary[:15],
        "board_stats": board_stats,
        "research_variables": research_variables,
        "review_queue": review_queue,
    }
    (OUTPUTS / "week8_workbook_data.json").write_text(
        json.dumps(workbook_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_summary_md(summary)

    manifest = build_manifest()
    write_csv(DERIVED / "week8_submission_manifest.csv", manifest)

    log_lines = [
        f"Week 8 pipeline finished at {run_time}",
        f"Input rows: subscription={len(subscription)}, snapshot={len(snapshot)}, transfer={len(transfer)}",
        f"Derived broad PE/VC records={broad_pevc_records}",
        f"P1 review items={p1_review_items}",
        "Outputs written under data/derived, review, database, and outputs.",
    ]
    (LOGS / "week8_pipeline.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print("\n".join(log_lines))


if __name__ == "__main__":
    main()
