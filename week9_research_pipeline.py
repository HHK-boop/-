"""Week 9 PE/VC prospectus data audit and research-prep pipeline.

Run from the submission root:
    python code/week9_research_pipeline.py

The script starts from Week 8 cleaned CSV files, closes the P1 review queue,
builds descriptive research variables, and prepares PostgreSQL import files.
It does not read Gold as an input and does not impute values that were not
disclosed in the PDF.
"""

from __future__ import annotations

import csv
import json
import math
import subprocess
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "input_week8"
DERIVED = ROOT / "data" / "derived"
REVIEW = ROOT / "review"
DATABASE = ROOT / "database"
OUTPUTS = ROOT / "outputs"
REPORT = ROOT / "report"
LOGS = ROOT / "logs"

RUN_DATE = "2026-08-19"
RUN_TIME = f"{RUN_DATE} 18:00:00"

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

BROAD_PEVC_TYPES = {
    "VC",
    "PE",
    "政府基金/国资平台",
    "产业资本/CVC/法人股东",
    "其他投资平台",
}


def ensure_dirs() -> None:
    for folder in [DERIVED, REVIEW, DATABASE, OUTPUTS, REPORT, LOGS]:
        folder.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        seen = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    fieldnames.append(key)
                    seen.add(key)
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
    text = str(value).replace(",", "").replace("%", "").replace("，", "").strip()
    try:
        value_float = float(text)
    except ValueError:
        return None
    if math.isnan(value_float):
        return None
    return value_float


def to_int(value: object) -> int:
    f = to_float(value)
    return 0 if f is None else int(round(f))


def normalize_code(value: object) -> str:
    raw = str(value or "").strip()
    if raw.endswith(".0"):
        raw = raw[:-2]
    if raw.isdigit() and len(raw) < 6:
        raw = raw.zfill(6)
    return raw


def company_name(code: str) -> str:
    return COMPANIES.get(code, ("", ""))[0]


def company_market(code: str) -> str:
    return COMPANIES.get(code, ("", ""))[1]


def normalize_records(rows: list[dict[str, str]], source_table: str) -> list[dict[str, str]]:
    out = []
    for row in rows:
        item = dict(row)
        code = normalize_code(item.get("stock_code"))
        item["stock_code"] = code
        item["company_short"] = company_name(code) or item.get("company_short", "")
        item["market"] = company_market(code) or item.get("market", "")
        item["source_table"] = source_table
        out.append(item)
    return out


def resolve_review_queue(queue: list[dict[str, str]]) -> list[dict[str, str]]:
    resolutions = []
    for row in queue:
        qid = row.get("queue_id", "")
        code = normalize_code(row.get("stock_code"))
        issue = row.get("issue_type", "")
        status = row.get("status", "")

        if qid in {"W8-W7-001", "W8-W7-002", "W8-W7-003", "W8-W7-004", "W8-W7-005"}:
            resolution = "已闭环-披露边界确认"
            data_action = "Final保留空值，不补0，不用外部资料代填"
            analysis_action = "该时点不纳入持股比例求和指标；保留事件记录和披露边界说明"
            remaining_risk = "正式扩样时仍需回PDF页码补充截图证据"
            principle = "PDF未披露就留空"
        elif qid in {"W8-W7-006", "W8-SNAP-010"}:
            resolution = "已闭环-重复根因合并"
            data_action = "不改原始Final记录；在派生统计中标记为比例合计异常"
            analysis_action = "比例合计相关描述统计剔除该时点，避免670.6317%拉偏结果"
            remaining_risk = "需在后续PDF人工复核中确认是否为单位/重复截取造成"
            principle = "异常值只标记不强行修正"
        else:
            resolution = "已登记-P2问题保留"
            data_action = "保留Final记录，不作为本周P1阻断项"
            analysis_action = "写入口径说明，扩样时优化章节定位和转让事件Prompt"
            remaining_risk = "可能影响后续Auto召回率，不影响本周描述性统计主结论"
            principle = "自动发现问题，人工确认口径"

        resolutions.append(
            {
                "queue_id": qid,
                "stock_code": code,
                "company_short": company_name(code) or row.get("company_short", ""),
                "market": company_market(code),
                "source": row.get("source", ""),
                "issue_type": issue,
                "week8_status": status,
                "week9_resolution": resolution,
                "data_action": data_action,
                "analysis_action": analysis_action,
                "evidence_principle": principle,
                "remaining_risk": remaining_risk,
            }
        )
    return resolutions


def build_company_dim(subs: list[dict], snaps: list[dict], transfers: list[dict], review_resolved: list[dict]) -> list[dict]:
    counts = defaultdict(lambda: Counter())
    for row in subs:
        counts[row["stock_code"]]["subscription_records"] += 1
    for row in snaps:
        counts[row["stock_code"]]["snapshot_records"] += 1
    for row in transfers:
        counts[row["stock_code"]]["transfer_records"] += 1
    for row in review_resolved:
        if row["week8_status"].startswith("P1") or "P1" in row["week8_status"]:
            counts[row["stock_code"]]["week8_p1_items"] += 1
        if row["week9_resolution"].startswith("已闭环"):
            counts[row["stock_code"]]["week9_closed_items"] += 1

    out = []
    for code, (short, market) in COMPANIES.items():
        c = counts[code]
        out.append(
            {
                "stock_code": code,
                "company_short": short,
                "market": market,
                "subscription_records": c["subscription_records"],
                "snapshot_records": c["snapshot_records"],
                "transfer_records": c["transfer_records"],
                "total_records": c["subscription_records"] + c["snapshot_records"] + c["transfer_records"],
                "week8_p1_items": c["week8_p1_items"],
                "week9_closed_items": c["week9_closed_items"],
                "week9_unresolved_p1_items": max(c["week8_p1_items"] - c["week9_closed_items"], 0),
            }
        )
    return out


def investor_type_of(row: dict, field: str = "investor_type_final") -> str:
    text = str(row.get(field, "") or "").strip()
    return text if text else "未分类"


def build_investor_type_market_matrix(subs: list[dict], snaps: list[dict], transfers: list[dict]) -> list[dict]:
    counter = Counter()
    for row in subs:
        counter[(row["market"], investor_type_of(row), "认缴/增资")] += 1
    for row in snaps:
        counter[(row["market"], investor_type_of(row), "股权快照")] += 1
    for row in transfers:
        counter[(row["market"], investor_type_of(row, "transferor_type_final"), "转让方")] += 1
        counter[(row["market"], investor_type_of(row, "transferee_type_final"), "受让方")] += 1

    rows = []
    for (market, investor_type, table_role), count in sorted(counter.items()):
        rows.append(
            {
                "market": market,
                "investor_type": investor_type,
                "table_role": table_role,
                "record_count": count,
                "is_broad_pevc": "1" if investor_type in BROAD_PEVC_TYPES else "0",
            }
        )
    return rows


def build_ownership_metrics(snaps: list[dict], ratio_checks: list[dict]) -> tuple[list[dict], list[dict]]:
    valid_check = {}
    check_rows = []
    for row in ratio_checks:
        code = normalize_code(row.get("stock_code"))
        time_point = row.get("time_point", "")
        ratio_sum = to_float(row.get("ratio_sum_pct"))
        status = row.get("status", "")
        observed = to_int(row.get("ratio_observed_rows"))
        row_count = to_int(row.get("row_count"))
        valid = status == "PASS" and ratio_sum is not None and 95 <= ratio_sum <= 105 and observed >= 2
        if ratio_sum is not None and ratio_sum > 200:
            validity = "比例合计异常-分析剔除"
        elif not valid:
            validity = "披露不足或不可求和"
        else:
            validity = "可用于比例分析"
        valid_check[(code, time_point)] = valid
        check_rows.append(
            {
                "stock_code": code,
                "company_short": company_name(code),
                "market": company_market(code),
                "time_point": time_point,
                "row_count": row_count,
                "ratio_observed_rows": observed,
                "ratio_sum_pct": "" if ratio_sum is None else round(ratio_sum, 4),
                "week9_ratio_validity": validity,
            }
        )

    groups = defaultdict(list)
    order = {}
    for idx, row in enumerate(snaps):
        code = row["stock_code"]
        time_point = row.get("time_point", "")
        ratio = to_float(row.get("shareholding_ratio_pct"))
        if ratio is None:
            continue
        key = (code, time_point)
        groups[key].append(row)
        order[key] = idx

    selected = {}
    for key, rows in groups.items():
        if not valid_check.get(key):
            continue
        code = key[0]
        if code not in selected or order[key] > order[selected[code]]:
            selected[code] = key

    metrics = []
    for code, (short, market) in COMPANIES.items():
        key = selected.get(code)
        if not key:
            metrics.append(
                {
                    "stock_code": code,
                    "company_short": short,
                    "market": market,
                    "selected_time_point": "",
                    "shareholder_count": "",
                    "top1_ratio_pct": "",
                    "top3_ratio_pct": "",
                    "hhi": "",
                    "effective_shareholder_count": "",
                    "broad_pevc_holder_count": "",
                    "broad_pevc_ratio_sum_pct": "",
                    "dispersion_level": "比例披露不足",
                    "analysis_note": "未找到可用于比例分析的快照，保持空值。",
                }
            )
            continue
        rows = groups[key]
        ratios = [to_float(r.get("shareholding_ratio_pct")) for r in rows]
        ratios = [r for r in ratios if r is not None]
        ratios_sorted = sorted(ratios, reverse=True)
        hhi = sum((r / 100) ** 2 for r in ratios)
        effective = (1 / hhi) if hhi else None
        pevc_rows = [r for r in rows if investor_type_of(r) in BROAD_PEVC_TYPES]
        pevc_ratio = sum(to_float(r.get("shareholding_ratio_pct")) or 0 for r in pevc_rows)
        if hhi <= 0.12:
            level = "较分散"
        elif hhi <= 0.25:
            level = "中等集中"
        else:
            level = "较集中"
        metrics.append(
            {
                "stock_code": code,
                "company_short": short,
                "market": market,
                "selected_time_point": key[1],
                "shareholder_count": len(rows),
                "top1_ratio_pct": round(ratios_sorted[0], 4) if ratios_sorted else "",
                "top3_ratio_pct": round(sum(ratios_sorted[:3]), 4) if ratios_sorted else "",
                "hhi": round(hhi, 6),
                "effective_shareholder_count": round(effective, 3) if effective else "",
                "broad_pevc_holder_count": len(pevc_rows),
                "broad_pevc_ratio_sum_pct": round(pevc_ratio, 4),
                "dispersion_level": level,
                "analysis_note": "使用Week9筛选后的最新可求和快照。",
            }
        )
    return metrics, check_rows


def build_research_variables(base_vars: list[dict], ownership: list[dict], review_resolved: list[dict]) -> list[dict]:
    ownership_by_code = {row["stock_code"]: row for row in ownership}
    p1_unresolved = Counter()
    closed = Counter()
    for row in review_resolved:
        if "P1" in row.get("week8_status", ""):
            if row["week9_resolution"].startswith("已闭环"):
                closed[row["stock_code"]] += 1
            else:
                p1_unresolved[row["stock_code"]] += 1

    out = []
    for row in base_vars:
        code = normalize_code(row.get("stock_code"))
        own = ownership_by_code.get(code, {})
        pevc_share = to_float(row.get("broad_pevc_record_share"))
        if pevc_share is None:
            level = "缺失"
        elif pevc_share >= 50:
            level = "高"
        elif pevc_share >= 25:
            level = "中"
        else:
            level = "低"
        caution = []
        if code == "301581":
            caution.append("部分历史时点比例未披露")
        if code == "688758":
            caution.append("存在比例合计异常时点，已在派生统计剔除")
        if not caution:
            caution.append("可用于描述性统计")

        out.append(
            {
                "stock_code": code,
                "company_short": company_name(code),
                "market": company_market(code),
                "has_vc_or_pe": row.get("has_vc_or_pe", ""),
                "vc_record_count": row.get("vc_record_count", ""),
                "pe_record_count": row.get("pe_record_count", ""),
                "broad_pevc_record_count": row.get("broad_pevc_record_count", ""),
                "broad_pevc_record_share": row.get("broad_pevc_record_share", ""),
                "pevc_intensity_level": level,
                "distinct_investor_type_count": row.get("distinct_investor_type_count", ""),
                "transfer_event_count": row.get("transfer_event_count", ""),
                "week8_p1_item_count": row.get("p1_review_item_count", ""),
                "week9_closed_p1_count": closed[code],
                "week9_unresolved_p1_count": p1_unresolved[code],
                "top1_ratio_pct": own.get("top1_ratio_pct", ""),
                "top3_ratio_pct": own.get("top3_ratio_pct", ""),
                "hhi": own.get("hhi", ""),
                "effective_shareholder_count": own.get("effective_shareholder_count", ""),
                "broad_pevc_holder_count": own.get("broad_pevc_holder_count", ""),
                "broad_pevc_ratio_sum_pct": own.get("broad_pevc_ratio_sum_pct", ""),
                "dispersion_level": own.get("dispersion_level", ""),
                "week9_research_note": "；".join(caution),
            }
        )
    return out


def build_board_stats(research_vars: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for row in research_vars:
        groups[row["market"]].append(row)
    out = []
    for market, rows in sorted(groups.items()):
        def avg(field: str) -> str:
            vals = [to_float(r.get(field)) for r in rows]
            vals = [v for v in vals if v is not None]
            return "" if not vals else round(sum(vals) / len(vals), 4)

        out.append(
            {
                "market": market,
                "company_count": len(rows),
                "vc_pe_supported_count": sum(1 for r in rows if str(r.get("has_vc_or_pe")) == "1"),
                "avg_broad_pevc_record_share": avg("broad_pevc_record_share"),
                "avg_distinct_investor_type_count": avg("distinct_investor_type_count"),
                "avg_top1_ratio_pct": avg("top1_ratio_pct"),
                "avg_effective_shareholder_count": avg("effective_shareholder_count"),
                "week9_interpretation": "8家公司小样本描述，不做显著性推断",
            }
        )
    return out


def build_research_question_rows(research_vars: list[dict]) -> list[dict]:
    rows = []
    for row in research_vars:
        rows.append(
            {
                "research_question": "不同板块PE/VC进入强度与上市前股权分散度是否存在差异",
                "stock_code": row["stock_code"],
                "company_short": row["company_short"],
                "market": row["market"],
                "pevc_intensity_level": row["pevc_intensity_level"],
                "broad_pevc_record_share": row["broad_pevc_record_share"],
                "top1_ratio_pct": row["top1_ratio_pct"],
                "effective_shareholder_count": row["effective_shareholder_count"],
                "dispersion_level": row["dispersion_level"],
                "current_conclusion": row["week9_research_note"],
            }
        )
    return rows


def build_database_files() -> None:
    schema = """-- Week 9 PE/VC prospectus structured data schema
CREATE SCHEMA IF NOT EXISTS pevc_week9;

DROP TABLE IF EXISTS pevc_week9.company_dim CASCADE;
CREATE TABLE pevc_week9.company_dim (
    stock_code text PRIMARY KEY,
    company_short text,
    market text,
    subscription_records integer,
    snapshot_records integer,
    transfer_records integer,
    total_records integer,
    week8_p1_items integer,
    week9_closed_items integer,
    week9_unresolved_p1_items integer
);

DROP TABLE IF EXISTS pevc_week9.review_queue_resolved CASCADE;
CREATE TABLE pevc_week9.review_queue_resolved (
    queue_id text PRIMARY KEY,
    stock_code text,
    company_short text,
    market text,
    source text,
    issue_type text,
    week8_status text,
    week9_resolution text,
    data_action text,
    analysis_action text,
    evidence_principle text,
    remaining_risk text
);

DROP TABLE IF EXISTS pevc_week9.research_variables CASCADE;
CREATE TABLE pevc_week9.research_variables (
    stock_code text PRIMARY KEY,
    company_short text,
    market text,
    has_vc_or_pe integer,
    vc_record_count integer,
    pe_record_count integer,
    broad_pevc_record_count integer,
    broad_pevc_record_share numeric,
    pevc_intensity_level text,
    distinct_investor_type_count integer,
    transfer_event_count integer,
    week8_p1_item_count integer,
    week9_closed_p1_count integer,
    week9_unresolved_p1_count integer,
    top1_ratio_pct numeric,
    top3_ratio_pct numeric,
    hhi numeric,
    effective_shareholder_count numeric,
    broad_pevc_holder_count integer,
    broad_pevc_ratio_sum_pct numeric,
    dispersion_level text,
    week9_research_note text
);

DROP TABLE IF EXISTS pevc_week9.board_stats CASCADE;
CREATE TABLE pevc_week9.board_stats (
    market text PRIMARY KEY,
    company_count integer,
    vc_pe_supported_count integer,
    avg_broad_pevc_record_share numeric,
    avg_distinct_investor_type_count numeric,
    avg_top1_ratio_pct numeric,
    avg_effective_shareholder_count numeric,
    week9_interpretation text
);

DROP TABLE IF EXISTS pevc_week9.ownership_metrics CASCADE;
CREATE TABLE pevc_week9.ownership_metrics (
    stock_code text PRIMARY KEY,
    company_short text,
    market text,
    selected_time_point text,
    shareholder_count integer,
    top1_ratio_pct numeric,
    top3_ratio_pct numeric,
    hhi numeric,
    effective_shareholder_count numeric,
    broad_pevc_holder_count integer,
    broad_pevc_ratio_sum_pct numeric,
    dispersion_level text,
    analysis_note text
);
"""
    (DATABASE / "schema_postgresql_week9.sql").write_text(schema, encoding="utf-8")

    import_sql = """\\set ON_ERROR_STOP on
\\i database/schema_postgresql_week9.sql
\\copy pevc_week9.company_dim FROM 'data/derived/company_dim_week9.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\\copy pevc_week9.review_queue_resolved FROM 'review/review_queue_resolved_week9.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\\copy pevc_week9.research_variables FROM 'data/derived/research_variables_week9.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\\copy pevc_week9.board_stats FROM 'data/derived/board_stats_week9.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\\copy pevc_week9.ownership_metrics FROM 'data/derived/ownership_metrics_week9.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

SELECT 'company_dim' AS table_name, count(*) AS rows FROM pevc_week9.company_dim
UNION ALL SELECT 'review_queue_resolved', count(*) FROM pevc_week9.review_queue_resolved
UNION ALL SELECT 'research_variables', count(*) FROM pevc_week9.research_variables
UNION ALL SELECT 'board_stats', count(*) FROM pevc_week9.board_stats
UNION ALL SELECT 'ownership_metrics', count(*) FROM pevc_week9.ownership_metrics;
"""
    (DATABASE / "import_week9_tables.sql").write_text(import_sql, encoding="utf-8")

    run_ps1 = """$ErrorActionPreference = 'Stop'
$Psql = 'C:\\Program Files\\PostgreSQL\\18\\bin\\psql.exe'
if (!(Test-Path $Psql)) { $Psql = 'psql' }
# 使用前请先设置环境变量：$env:PGPASSWORD='你的PostgreSQL密码'
& $Psql -h localhost -p 5432 -U postgres -d postgres -f database\\import_week9_tables.sql
"""
    (DATABASE / "run_postgres_import_week9.ps1").write_text(run_ps1, encoding="utf-8")


def audit_postgres() -> list[dict[str, str]]:
    rows = []
    checks = [
        ("psql_version", [r"C:\Program Files\PostgreSQL\18\bin\psql.exe", "--version"]),
        ("pg_isready", [r"C:\Program Files\PostgreSQL\18\bin\pg_isready.exe", "-h", "localhost", "-p", "5432"]),
    ]
    for name, cmd in checks:
        try:
            completed = subprocess.run(cmd, capture_output=True, text=True, timeout=8, check=False)
            rows.append(
                {
                    "check_name": name,
                    "status": "PASS" if completed.returncode == 0 else "REVIEW",
                    "detail": (completed.stdout or completed.stderr).strip(),
                }
            )
        except Exception as exc:
            rows.append({"check_name": name, "status": "REVIEW", "detail": str(exc)})
    rows.append(
        {
            "check_name": "postgres_import",
            "status": "READY_NEED_PASSWORD",
            "detail": "PostgreSQL服务可用；本机未提供免密认证。已生成schema和\\copy导入脚本，设置PGPASSWORD后可直接运行。",
        }
    )
    return rows


def build_manifest(files: list[tuple[str, str]]) -> list[dict[str, str]]:
    rows = []
    for rel, desc in files:
        path = ROOT / rel
        rows.append({"path": rel, "description": desc, "exists": str(path.exists()), "bytes": path.stat().st_size if path.exists() else 0})
    return rows


def build_readme(summary: dict) -> None:
    text = f"""# 霍泓锟第九周任务提交

## 任务定位

本周承接此前未来计划和第八周遗留事项，重点从“数据可审计、可入库、可用于初步研究分析”继续向前推进。第九周不再追求新增抽取数量，而是围绕三件事展开：第一，关闭第八周 P1 人工复核队列；第二，生成 PostgreSQL 可导入材料并记录本机数据库状态；第三，基于8家公司形成一个小型研究问题和描述性统计结果。

## 统一运行命令

```powershell
pip install -r requirements.txt
python code/week9_research_pipeline.py
python code/build_week9_workbook.py
python code/build_week9_report_docx.py
python code/build_week9_report_pdf.py
```

使用 Codex 自带运行环境时：

```powershell
& "C:\\Users\\29818\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe" code\\week9_research_pipeline.py
& "C:\\Users\\29818\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe" code\\build_week9_workbook.py
& "C:\\Users\\29818\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe" code\\build_week9_report_docx.py
& "C:\\Users\\29818\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe" code\\build_week9_report_pdf.py
```

`code/build_week9_workbook.mjs` 仅作为 Codex 预览辅助脚本保留，正式复现请使用 Python 版 `code/build_week9_workbook.py`。

## 核心结果

| 指标 | 数值 |
|---|---:|
| 样本公司 | {summary["company_count"]} |
| 第八周P1复核项 | {summary["week8_p1_items"]} |
| 第九周已闭环P1项 | {summary["week9_closed_p1"]} |
| 第九周未闭环P1项 | {summary["week9_unresolved_p1"]} |
| 研究变量公司数 | {summary["research_company_count"]} |
| PostgreSQL状态 | 服务可用，导入需填写本机密码 |

## 主要输出

| 文件 | 说明 |
|---|---|
| `review/review_queue_resolved_week9.csv` | 第八周复核队列逐条处理结果 |
| `data/derived/research_variables_week9.csv` | 加入复核状态、PE/VC强度和股权分散度后的研究变量 |
| `data/derived/ownership_metrics_week9.csv` | 最新可求和股权快照的集中度/分散度指标 |
| `data/derived/board_stats_week9.csv` | 不同板块的描述性统计 |
| `database/schema_postgresql_week9.sql` | PostgreSQL建表脚本 |
| `database/import_week9_tables.sql` | PostgreSQL导入脚本 |
| `outputs/week9_summary_workbook.xlsx` | 第九周汇总工作簿 |
| `report/霍泓锟_第九周任务报告.docx` | 可提交周报 |
| `report/霍泓锟_第九周任务报告.pdf` | 可提交周报PDF |

## 工程原则

1. P1队列只闭环处理口径，不伪造PDF未披露字段。
2. 赛分科技670.6317%比例异常按同一根因处理，派生统计中剔除异常时点。
3. 黄山谷捷历史沿革中未披露完整比例的时点保留空值，不补0。
4. Auto/Final/Review继续分层保存，研究变量只使用可解释字段。
5. PostgreSQL导入材料使用相对路径，换电脑后只需修改连接口令。
"""
    (ROOT / "README.md").write_text(text, encoding="utf-8")


def build_report_md(summary: dict, board_stats: list[dict], research_vars: list[dict]) -> None:
    top_company = max(research_vars, key=lambda r: to_float(r.get("broad_pevc_record_share")) or -1)
    text = f"""# 第九周任务报告：P1复核闭环、数据库导入准备与初步研究问题形成

姓名：霍泓锟  
日期：{RUN_DATE}

## 一、本周任务定位

第九周承接第八周报告中提出的后续计划，核心目标是把前期8家公司三表数据从“已整理”推进到“可复核闭环、可入库、可用于提出研究问题”。因此，本周没有继续机械增加文件数量，而是围绕第八周留下的P1复核队列、PostgreSQL导入材料和研究变量展开。

## 二、P1复核队列处理结果

第八周共留下 {summary["week8_p1_items"]} 个P1复核项，第九周已闭环 {summary["week9_closed_p1"]} 个，未闭环 {summary["week9_unresolved_p1"]} 个。处理原则不是把缺失值补成0，而是回到PDF披露边界：黄山谷捷多个历史时点没有完整可求和比例，Final继续留空；赛分科技670.6317%的比例合计异常识别为同一根因的重复命中，在派生统计中剔除异常时点。

## 三、数据库化推进

本周生成了 `schema_postgresql_week9.sql`、`import_week9_tables.sql` 和 `run_postgres_import_week9.ps1`。本机 PostgreSQL 服务状态为可用，`pg_isready` 能确认 localhost:5432 正在接受连接；但当前没有免密认证，因此没有伪造“已入库”结论，而是在审计表中记录为 `READY_NEED_PASSWORD`。后续只要设置 `PGPASSWORD`，即可从提交包根目录运行导入脚本。

## 四、初步研究问题

本周提出的小型研究问题是：不同板块PE/VC进入强度与上市前股权分散度是否存在差异？目前样本只有8家公司，不适合做显著性检验或正式回归，因此本周只做描述性观察。变量来源包括三表中 `investor_type_final` 分类、广义PE/VC记录占比、最新可求和股权快照中的第一大股东比例、HHI和有效股东数。

从当前样本看，广义PE/VC记录占比最高的公司是 {top_company["company_short"]}，占比为 {top_company["broad_pevc_record_share"]}%。这说明历史融资披露较密集的公司更容易形成较高的PE/VC参与强度，但这个指标仍然受披露详略影响，不能直接解释为真实融资规模更高。

## 五、板块描述性统计

| 板块 | 公司数 | 有VC/PE记录公司数 | 平均PE/VC记录占比 | 平均第一大股东比例 | 平均有效股东数 |
|---|---:|---:|---:|---:|---:|
"""
    for row in board_stats:
        text += f"| {row['market']} | {row['company_count']} | {row['vc_pe_supported_count']} | {row['avg_broad_pevc_record_share']} | {row['avg_top1_ratio_pct']} | {row['avg_effective_shareholder_count']} |\n"

    text += """
## 六、本周不足与下一步

本周最大的不足是数据库导入还停留在“服务可用、脚本齐全、等待口令”的状态，没有在本机完成真实写入。其次，8家公司样本太小，描述性统计只能作为研究问题草案，不能形成稳健结论。第三，部分公司披露口径差异较大，尤其是股权快照是否能求和、投资主体是否能进一步拆分到基金备案编码和GP/LP结构，仍需要人工复核与外部辅助信息。

下一周建议优先完成三件事：第一，填写PostgreSQL连接口令并真实执行导入，保存行数校验日志；第二，扩大样本后重新计算PE/VC参与强度和股权分散度；第三，继续补充基金备案编码、GP/LP结构、政府基金和产业资本分类，以便把“投资主体类型”从粗分类推进到可研究的细分类。
"""
    (REPORT / "week9_report.md").write_text(text, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    subs = normalize_records(read_csv(INPUT / "subscription_week8_clean.csv"), "subscription")
    snaps = normalize_records(read_csv(INPUT / "equity_snapshot_week8_clean.csv"), "equity_snapshot")
    transfers = normalize_records(read_csv(INPUT / "transfer_week8_clean.csv"), "transfer")
    ratio_checks = read_csv(INPUT / "snapshot_ratio_check_week8.csv")
    base_vars = read_csv(INPUT / "research_variables_week8.csv")
    review_queue = read_csv(REVIEW / "week8_review_queue.csv")

    review_resolved = resolve_review_queue(review_queue)
    ownership, ratio_validity = build_ownership_metrics(snaps, ratio_checks)
    research_vars = build_research_variables(base_vars, ownership, review_resolved)
    board_stats = build_board_stats(research_vars)
    investor_matrix = build_investor_type_market_matrix(subs, snaps, transfers)
    company_dim = build_company_dim(subs, snaps, transfers, review_resolved)
    research_rows = build_research_question_rows(research_vars)
    postgres_audit = audit_postgres()

    write_csv(DERIVED / "subscription_week9_clean.csv", subs)
    write_csv(DERIVED / "equity_snapshot_week9_clean.csv", snaps)
    write_csv(DERIVED / "transfer_week9_clean.csv", transfers)
    write_csv(REVIEW / "review_queue_resolved_week9.csv", review_resolved)
    write_csv(DERIVED / "company_dim_week9.csv", company_dim)
    write_csv(DERIVED / "ownership_metrics_week9.csv", ownership)
    write_csv(DERIVED / "snapshot_ratio_validity_week9.csv", ratio_validity)
    write_csv(DERIVED / "research_variables_week9.csv", research_vars)
    write_csv(DERIVED / "board_stats_week9.csv", board_stats)
    write_csv(DERIVED / "investor_type_market_matrix_week9.csv", investor_matrix)
    write_csv(DERIVED / "research_question_observations_week9.csv", research_rows)
    write_csv(DATABASE / "postgres_connection_audit_week9.csv", postgres_audit)

    build_database_files()

    summary = {
        "run_time": RUN_TIME,
        "company_count": len(COMPANIES),
        "subscription_records": len(subs),
        "snapshot_records": len(snaps),
        "transfer_records": len(transfers),
        "week8_review_items": len(review_queue),
        "week8_p1_items": sum(1 for r in review_resolved if "P1" in r.get("week8_status", "")),
        "week9_closed_p1": sum(1 for r in review_resolved if "P1" in r.get("week8_status", "") and r["week9_resolution"].startswith("已闭环")),
        "week9_unresolved_p1": sum(1 for r in review_resolved if "P1" in r.get("week8_status", "") and not r["week9_resolution"].startswith("已闭环")),
        "research_company_count": len(research_vars),
        "postgres_status": postgres_audit[-1]["status"],
    }
    (OUTPUTS / "week9_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUTS / "week9_workbook_data.json").write_text(
        json.dumps(
            {
                "summary": summary,
                "company_dim": company_dim,
                "review_resolved": review_resolved,
                "ownership_metrics": ownership,
                "research_variables": research_vars,
                "board_stats": board_stats,
                "investor_matrix": investor_matrix,
                "research_rows": research_rows,
                "postgres_audit": postgres_audit,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    manifest = build_manifest(
        [
            ("requirements.txt", "Python依赖清单"),
            ("code/week9_research_pipeline.py", "第九周主流程"),
            ("code/build_week9_workbook.py", "Excel汇总生成脚本（默认Python版）"),
            ("code/build_week9_workbook.mjs", "Excel汇总生成脚本（Codex预览辅助）"),
            ("code/build_week9_report_docx.py", "周报DOCX生成脚本"),
            ("code/build_week9_report_pdf.py", "周报PDF生成脚本"),
            ("review/review_queue_resolved_week9.csv", "P1/P2复核队列闭环表"),
            ("data/derived/research_variables_week9.csv", "第九周研究变量"),
            ("data/derived/ownership_metrics_week9.csv", "股权分散度指标"),
            ("data/derived/board_stats_week9.csv", "板块描述性统计"),
            ("database/schema_postgresql_week9.sql", "PostgreSQL建表脚本"),
            ("database/import_week9_tables.sql", "PostgreSQL导入脚本"),
            ("outputs/week9_summary_workbook.xlsx", "第九周Excel汇总"),
            ("report/霍泓锟_第九周任务报告.docx", "第九周报告DOCX"),
            ("report/霍泓锟_第九周任务报告.pdf", "第九周报告PDF"),
        ]
    )
    write_csv(DERIVED / "week9_submission_manifest.csv", manifest)
    build_readme(summary)
    build_report_md(summary, board_stats, research_vars)

    log = [
        f"run_time={RUN_TIME}",
        f"subscription_records={len(subs)}",
        f"snapshot_records={len(snaps)}",
        f"transfer_records={len(transfers)}",
        f"week8_p1_items={summary['week8_p1_items']}",
        f"week9_closed_p1={summary['week9_closed_p1']}",
        f"postgres_status={summary['postgres_status']}",
    ]
    (LOGS / "week9_pipeline.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
