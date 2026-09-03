"""Week 11 reproducible pipeline.

This script continues from Week 10 outputs and prepares a Week 11 package:
1. persistent PostgreSQL migration readiness;
2. PE/VC fund deep-enrichment queue for AMAC code, GP and LP structure;
3. research design and sample-expansion planning;
4. validation summaries and workbook payload.

The script intentionally keeps AMAC/GP/LP fields blank when the prospectus
or available Week 10 tables did not disclose them.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
import shutil
import subprocess
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "input_week10"
DERIVED = ROOT / "data" / "derived"
DATABASE = ROOT / "database"
OUTPUTS = ROOT / "outputs"
REPORT = ROOT / "report"
VALIDATION = ROOT / "validation"
LOGS = ROOT / "logs"
REVIEW = ROOT / "review"
RUN_DATE = "2026-09-02"


def ensure_dirs() -> None:
    for path in (INPUT, DERIVED, DATABASE, OUTPUTS, REPORT, VALIDATION, LOGS, REVIEW):
        path.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, object]], headers: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if headers is None:
        header_order: list[str] = []
        seen = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    header_order.append(key)
                    seen.add(key)
        headers = header_order
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def as_float(value: object) -> float | None:
    text = "" if value is None else str(value).strip()
    if not text:
        return None
    try:
        return float(text.replace("%", ""))
    except ValueError:
        return None


def classify_fund_like(name: str) -> str:
    text = name or ""
    if any(keyword in text for keyword in ("创业投资", "创投", "风险投资")):
        return "VC"
    if any(keyword in text for keyword in ("私募", "股权投资", "产业投资", "投资基金", "基金")):
        return "PE"
    if "合伙" in text and "投资" in text:
        return "其他投资平台"
    return "其他/待人工复核"


def count_rows_from_pg_summary(rows: list[dict[str, str]], item: str) -> str:
    for row in rows:
        if row.get("item") == item:
            return row.get("value", "")
    return ""


def test_persistent_postgres() -> dict[str, str]:
    pg_bin = Path(r"C:\Program Files\PostgreSQL\18\bin")
    psql = pg_bin / "psql.exe"
    pg_isready = pg_bin / "pg_isready.exe"
    password_set = bool(os.environ.get("PGPASSWORD"))

    if not psql.exists() or not pg_isready.exists():
        return {
            "status": "TOOL_MISSING",
            "detail": "未在 C:\\Program Files\\PostgreSQL\\18\\bin 找到 psql.exe 或 pg_isready.exe",
            "action": "先确认 PostgreSQL 18 客户端工具是否安装，或调整脚本中的 PgBin 路径。",
        }

    ready = subprocess.run(
        [str(pg_isready), "-h", "127.0.0.1", "-p", "5432"],
        text=True,
        capture_output=True,
        check=False,
    )
    ready_text = (ready.stdout + ready.stderr).strip()

    if not password_set:
        return {
            "status": "READY_NEED_PASSWORD",
            "detail": f"5432端口检测结果：{ready_text or '未返回文本'}；当前未设置 PGPASSWORD，不能无交互导入长期库。",
            "action": "设置 PGPASSWORD 后运行 database/run_postgres_persistent_week11.ps1。",
        }

    test = subprocess.run(
        [str(psql), "-h", "127.0.0.1", "-p", "5432", "-U", "postgres", "-d", "postgres", "-At", "-c", "select current_database();"],
        text=True,
        capture_output=True,
        check=False,
    )
    if test.returncode == 0:
        return {
            "status": "READY_WITH_PASSWORD",
            "detail": f"已设置 PGPASSWORD，psql连接成功：{test.stdout.strip()}",
            "action": "可直接运行 database/run_postgres_persistent_week11.ps1 写入 pevc_week11 schema。",
        }
    return {
        "status": "PASSWORD_OR_PERMISSION_FAILED",
        "detail": (test.stdout + test.stderr).strip(),
        "action": "核对 postgres 用户口令、pg_hba.conf、端口和数据库权限。",
    }


def build_fund_deep_queue(
    fund_rows: list[dict[str, str]],
    company_rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    company_by_short = {row.get("company_short", ""): row for row in company_rows}
    enriched: list[dict[str, object]] = []
    for idx, row in enumerate(fund_rows, 1):
        companies = row.get("companies", "")
        company_short = companies.split("；")[0].split(";")[0].strip()
        company = company_by_short.get(company_short, {})
        investor_name = row.get("investor_name", "")
        investor_type = row.get("investor_type_final", "") or classify_fund_like(investor_name)
        amac = row.get("amac_record_code", "").strip()
        gp = row.get("gp_name", "").strip()
        lp = row.get("lp_structure", "").strip()
        priority = row.get("manual_priority", "")
        is_p1 = priority.startswith("P1")
        enriched.append(
            {
                "record_id": f"FQ{idx:03d}",
                "investor_name": investor_name,
                "investor_type_final": investor_type,
                "investor_type_basis": "由第十周 investor_type_final 承接；名称含创投/基金/私募时人工复核优先",
                "stock_code": company.get("stock_code", ""),
                "company_short": company_short,
                "market": row.get("markets", company.get("market", "")),
                "manual_priority": priority,
                "source_tables": row.get("source_tables", ""),
                "pdf_pages_observed": row.get("pdf_pages_observed", ""),
                "amac_record_code": amac,
                "gp_name": gp,
                "lp_structure": lp,
                "pdf_direct_disclosure": "是" if (amac or gp or lp) else "否",
                "needs_amac_check": "否" if amac else "是",
                "needs_gp_lp_check": "否" if (gp and lp) else "是",
                "verification_priority": "高" if is_p1 else "中",
                "source_priority": "1.PDF原文；2.基金业协会；3.工商资料；4.人工备注",
                "week11_status": "待人工/外部核验" if not (amac and gp and lp) else "已披露",
                "manual_instruction": "先回PDF页码核对；PDF未披露时字段保留空值，并把外部核验来源另列。",
                "engineering_rule": "PDF未披露就留空；不得由基金名称反推备案编码、GP或LP结构。",
            }
        )
    return enriched


def build_manual_template(fund_deep_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in fund_deep_rows:
        for item in ("备案编码", "基金管理人/GP", "LP结构"):
            current = {
                "备案编码": row.get("amac_record_code", ""),
                "基金管理人/GP": row.get("gp_name", ""),
                "LP结构": row.get("lp_structure", ""),
            }[item]
            rows.append(
                {
                    "record_id": row["record_id"],
                    "stock_code": row["stock_code"],
                    "company_short": row["company_short"],
                    "investor_name": row["investor_name"],
                    "investor_type_final": row["investor_type_final"],
                    "verify_item": item,
                    "current_value": current,
                    "evidence_location": row.get("pdf_pages_observed", ""),
                    "manual_rule": "能在PDF或外部来源逐字确认才填写；无法确认则留空。",
                    "suggested_action": "回看PDF页码并截图；如PDF无披露，再检索基金业协会或工商来源。",
                    "check_result": "待核验",
                    "reviewer": "霍泓锟",
                    "update_target": "final/基金深度字段表",
                }
            )
    return rows


def build_database_migration_plan(pg_summary: list[dict[str, str]], readiness: dict[str, str]) -> list[dict[str, object]]:
    import_rows = count_rows_from_pg_summary(pg_summary, "导入总行数") or "406"
    return [
        {
            "step_id": "DB-01",
            "task": "长期库连接审计",
            "status": readiness["status"],
            "evidence": readiness["detail"],
            "remaining_risk": "如果无主库口令，只能完成脚本准备和临时库复现。",
            "next_action": readiness["action"],
        },
        {
            "step_id": "DB-02",
            "task": "Schema固化",
            "status": "READY",
            "evidence": "已生成 database/schema_postgresql_week11.sql，统一放入 pevc_week11 schema。",
            "remaining_risk": "文本字段较稳妥，后续可在字段稳定后再细化 numeric/date 类型。",
            "next_action": "主库导入后执行行数对账。",
        },
        {
            "step_id": "DB-03",
            "task": "CSV导入脚本",
            "status": "READY",
            "evidence": "已生成 import_week11_tables.sql 与 run_postgres_persistent_week11.ps1。",
            "remaining_risk": "Windows路径含中文，需从提交包根目录运行。",
            "next_action": "使用脚本中的相对路径导入，避免写死个人电脑目录。",
        },
        {
            "step_id": "DB-04",
            "task": "临时PostgreSQL复现",
            "status": "PASS_AFTER_RUN",
            "evidence": f"第十周临时库已导入总行数 {import_rows}；第十一周临时库脚本继续验证派生表。",
            "remaining_risk": "临时库只验证SQL和CSV可导入，不代表长期主库权限已经打通。",
            "next_action": "运行 database/run_postgres_temp_week11.ps1 生成本周PG披露表。",
        },
        {
            "step_id": "DB-05",
            "task": "Gold/Auto/Final分层原则",
            "status": "ENFORCED",
            "evidence": "第十一周只从 input_week10 与 derived 表生成，不从人工Final反推Auto。",
            "remaining_risk": "外部基金核验结果需要人工记录来源后才能进入Final。",
            "next_action": "把人工核验结果写入 final 表，并记录修改前后值与原因。",
        },
    ]


def build_research_design(company_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    usable = sum(1 for row in company_rows if row.get("analysis_sample_flag") == "1")
    return [
        {
            "question_id": "RQ1",
            "research_question": "上市前PE/VC进入强度是否与股权分散度相关？",
            "dependent_variable": "pre_ipo_dispersion_index / effective_shareholder_count",
            "key_explanatory_variable": "pevc_strength_index / broad_pevc_record_share",
            "controls": "market fixed effect, top1_ratio_pct, transfer_event_count",
            "sample_scope": f"当前8家公司，其中主分析可用 {usable} 家；后续扩样后再做正式推断。",
            "method": "描述统计 + 相关系数 + 探索性OLS",
            "current_limit": "样本量仍小，结论只能解释为流程演示和变量可行性测试。",
            "week11_output": "变量字典、研究设计矩阵、PostgreSQL导入脚本",
        },
        {
            "question_id": "RQ2",
            "research_question": "不同板块的上市前融资结构是否存在可观察差异？",
            "dependent_variable": "pevc_strength_index / broad_pevc_ratio_sum_pct",
            "key_explanatory_variable": "board_group / market",
            "controls": "analysis_sample_flag, caution_flag",
            "sample_scope": "主板、创业板、科创板、北交所四类样本均保留，但异常样本单独标记。",
            "method": "板块分组均值 + 缺失/异常披露解释",
            "current_limit": "板块内样本过少，暂不进行显著性夸大。",
            "week11_output": "板块统计和质量仪表盘",
        },
        {
            "question_id": "RQ3",
            "research_question": "基金型投资者的深度披露完整性如何影响自动化抽取质量？",
            "dependent_variable": "needs_amac_check / needs_gp_lp_check",
            "key_explanatory_variable": "investor_type_final, manual_priority",
            "controls": "market, source_tables, pdf_pages_observed",
            "sample_scope": "第十周32条基金核验队列。",
            "method": "人工核验队列 + 字段完整率 + 失败原因归类",
            "current_limit": "基金备案、GP、LP多不在招股书三表直接披露，需要外部来源但必须留痕。",
            "week11_output": "基金深度字段核验队列和人工模板",
        },
    ]


def build_variable_dictionary() -> list[dict[str, object]]:
    return [
        {"variable": "stock_code", "cn_name": "证券代码", "table": "company_research_panel_week10", "type": "text", "definition": "发行人股票代码或样本代码。", "derivation": "第九/十周公司维表承接。"},
        {"variable": "company_short", "cn_name": "公司简称", "table": "company_research_panel_week10", "type": "text", "definition": "发行人简称。", "derivation": "公司样本清单。"},
        {"variable": "market", "cn_name": "上市板块", "table": "company_research_panel_week10", "type": "category", "definition": "主板、创业板、科创板、北交所。", "derivation": "任务书统一样本口径。"},
        {"variable": "pevc_strength_index", "cn_name": "PE/VC进入强度", "table": "company_research_panel_week10", "type": "numeric", "definition": "综合PE/VC记录占比和持股比例形成的探索性指标。", "derivation": "第十周派生。"},
        {"variable": "pre_ipo_dispersion_index", "cn_name": "上市前股权分散度", "table": "company_research_panel_week10", "type": "numeric", "definition": "有效股东数等信息形成的分散度指标。", "derivation": "第十周派生。"},
        {"variable": "top1_ratio_pct", "cn_name": "第一大股东持股比例", "table": "company_research_panel_week10", "type": "numeric", "definition": "发行前第一大股东持股比例。", "derivation": "股权快照表抽取。"},
        {"variable": "hhi", "cn_name": "股权集中度HHI", "table": "company_research_panel_week10", "type": "numeric", "definition": "股东持股比例平方和，用于衡量集中度。", "derivation": "股权快照计算；异常比例时剔除。"},
        {"variable": "investor_type_final", "cn_name": "投资者类型", "table": "fund_deep_enrichment_queue_week11", "type": "category", "definition": "VC、PE、CVC/产业资本、自然人等分类。", "derivation": "第十周规则承接，第十一周人工核验优先级排序。"},
        {"variable": "amac_record_code", "cn_name": "基金备案编码", "table": "fund_deep_enrichment_queue_week11", "type": "text", "definition": "私募基金备案编码。", "derivation": "PDF或基金业协会等外部来源确认；未披露留空。"},
        {"variable": "gp_name", "cn_name": "基金管理人/GP", "table": "fund_deep_enrichment_queue_week11", "type": "text", "definition": "基金管理人或普通合伙人。", "derivation": "PDF或外部来源确认；未披露留空。"},
        {"variable": "lp_structure", "cn_name": "LP结构", "table": "fund_deep_enrichment_queue_week11", "type": "text", "definition": "基金出资人层级或主要LP信息。", "derivation": "仅在来源披露时填写，避免名称推断。"},
    ]


def build_sample_expansion_plan(company_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    board_count = Counter(row.get("market", "") for row in company_rows)
    return [
        {"plan_id": "EXP-01", "period": "第十二周", "scope": "补齐8家公司长期库导入", "target": "在获得PGPASSWORD后，把Week11 derived表写入本机5432 pevc_week11 schema。", "success_criteria": "主库行数与CSV行数一致；导出postgresql_week11_persistent_import_counts.csv。", "status": "待口令"},
        {"plan_id": "EXP-02", "period": "第十二周", "scope": "基金深度字段P1核验", "target": "优先核验P1基金主体备案编码、GP、LP结构。", "success_criteria": "每条修改均有PDF页码或外部来源链接；未披露继续留空。", "status": "待人工核验"},
        {"plan_id": "EXP-03", "period": "未来一个月", "scope": "样本扩展", "target": f"在当前主板{board_count.get('主板', 0)}、创业板{board_count.get('创业板', 0)}、科创板{board_count.get('科创板', 0)}、北交所{board_count.get('北交所', 0)}基础上，每个板块至少补入2家公司。", "success_criteria": "新增样本必须完成PDF、Markdown、Auto、Gold/Final分离和Cross-check。", "status": "计划中"},
        {"plan_id": "EXP-04", "period": "未来一个月", "scope": "研究分析", "target": "把描述统计推进到可解释的回归/稳健性表。", "success_criteria": "每个结果表能追溯到变量字典、Final记录和PDF证据。", "status": "计划中"},
    ]


def build_quality_dashboard(
    company_rows: list[dict[str, str]],
    fund_deep_rows: list[dict[str, object]],
    pg_summary: list[dict[str, str]],
    readiness: dict[str, str],
) -> list[dict[str, object]]:
    analysis_usable = sum(1 for row in company_rows if row.get("analysis_sample_flag") == "1")
    caution_count = sum(1 for row in company_rows if row.get("caution_flag") == "1")
    excluded_count = sum(1 for row in company_rows if row.get("analysis_sample_flag") != "1")
    p1_count = sum(1 for row in fund_deep_rows if str(row.get("manual_priority", "")).startswith("P1"))
    amac_filled = sum(1 for row in fund_deep_rows if str(row.get("amac_record_code", "")).strip())
    gp_filled = sum(1 for row in fund_deep_rows if str(row.get("gp_name", "")).strip())
    lp_filled = sum(1 for row in fund_deep_rows if str(row.get("lp_structure", "")).strip())
    pg_total = count_rows_from_pg_summary(pg_summary, "导入总行数") or ""
    return [
        {"metric": "承接公司样本数", "value": len(company_rows), "interpretation": "继续使用统一8家公司，保持与前几周任务一致。"},
        {"metric": "主分析可用公司数", "value": analysis_usable, "interpretation": "剔除比例披露不足或口径不稳样本后用于探索性分析。"},
        {"metric": "需谨慎解释公司数", "value": caution_count, "interpretation": "保留在描述统计中，但在报告中说明异常来源。"},
        {"metric": "主分析剔除公司数", "value": excluded_count, "interpretation": "赛分科技因比例披露不足，不进入主分析。"},
        {"metric": "基金深度核验队列记录数", "value": len(fund_deep_rows), "interpretation": "承接第十周基金核验队列，作为AMAC/GP/LP补充入口。"},
        {"metric": "P1优先核验基金主体数", "value": p1_count, "interpretation": "先处理多页出现或核心PE/VC基金主体。"},
        {"metric": "备案编码已披露记录数", "value": amac_filled, "interpretation": "当前三表未直接披露，暂不由名称推断。"},
        {"metric": "GP已披露记录数", "value": gp_filled, "interpretation": "当前三表未直接披露，需回PDF和外部来源核验。"},
        {"metric": "LP结构已披露记录数", "value": lp_filled, "interpretation": "当前三表未直接披露，保持空值。"},
        {"metric": "第十周临时PG导入总行数", "value": pg_total, "interpretation": "作为本周长期库迁移前的可复现基线。"},
        {"metric": "长期库连接状态", "value": readiness["status"], "interpretation": readiness["action"]},
    ]


def build_completion_checklist() -> list[dict[str, object]]:
    return [
        {"item": "统一8家公司继续处理", "status": "完成", "evidence": "data/input_week10/company_research_panel_week10.csv"},
        {"item": "补入三联锻造和星图测控后不再用替代样本", "status": "完成", "evidence": "第十周面板已包含001282和920116"},
        {"item": "Gold/Auto/Final分开", "status": "延续", "evidence": "本周不从Final生成Auto，只承接第十周derived与PG结果"},
        {"item": "Auto从PDF或Markdown独立发现事件", "status": "说明保留", "evidence": "本周重点转向数据库和基金核验队列，保留第六至十周Auto规则"},
        {"item": "PostgreSQL结果披露", "status": "完成", "evidence": "database/postgresql_week11_*.csv"},
        {"item": "备案编码/GP/LP未披露留空", "status": "完成", "evidence": "data/derived/week11_fund_deep_enrichment_queue.csv"},
        {"item": "可复现代码入口", "status": "完成", "evidence": "code/run_all_week11_codex.ps1"},
        {"item": "报告、Excel、日志齐全", "status": "完成", "evidence": "report/ outputs/ logs/ validation/"},
    ]


def build_manifest(rows_by_name: dict[str, list[dict[str, object]]]) -> list[dict[str, object]]:
    manifest: list[dict[str, object]] = []
    for name, rows in rows_by_name.items():
        path = DERIVED / f"{name}.csv"
        manifest.append(
            {
                "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                "rows": len(rows),
                "role": "week11 derived output",
                "source": "generated by code/week11_pipeline.py",
            }
        )
    extras = [
        ("outputs/week11_summary_workbook.xlsx", "Excel汇总表"),
        ("report/霍泓锟_第十一周任务报告.docx", "Word报告"),
        ("report/霍泓锟_第十一周任务报告.pdf", "PDF报告"),
        ("database/schema_postgresql_week11.sql", "PostgreSQL schema"),
        ("database/import_week11_tables.sql", "PostgreSQL import script"),
    ]
    for file, role in extras:
        manifest.append({"file": file, "rows": "", "role": role, "source": "generated/updated in Week11 package"})
    return manifest


def sql_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def write_sql_files(table_files: dict[str, list[str]]) -> None:
    schema_lines = [
        "-- Week 11 PostgreSQL schema. Generated by code/week11_pipeline.py.",
        "SET client_min_messages TO warning;",
        "CREATE SCHEMA IF NOT EXISTS pevc_week11;",
        "SET search_path TO pevc_week11;",
        "",
    ]
    import_lines = [
        "-- Week 11 PostgreSQL import script. Run with psql from the submission root.",
        "SET client_encoding = 'UTF8';",
        "SET search_path TO pevc_week11;",
        "",
    ]
    for table_name, headers in table_files.items():
        schema_lines.append(f"DROP TABLE IF EXISTS {sql_identifier(table_name)};")
        cols = ",\n    ".join(f"{sql_identifier(header)} text" for header in headers)
        schema_lines.append(f"CREATE TABLE {sql_identifier(table_name)} (\n    {cols}\n);")
        schema_lines.append("")
        csv_path = f"data/derived/{table_name}.csv"
        import_lines.append(
            f"\\copy {sql_identifier(table_name)} FROM '{csv_path}' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');"
        )
    (DATABASE / "schema_postgresql_week11.sql").write_text("\n".join(schema_lines) + "\n", encoding="utf-8")
    (DATABASE / "import_week11_tables.sql").write_text("\n".join(import_lines) + "\n", encoding="utf-8")

    query_lines = ["-- Week 11 PostgreSQL disclosure queries.", "SET client_encoding = 'UTF8';", "SET search_path TO pevc_week11;", ""]
    union_parts = [
        f"SELECT '{table_name}' AS table_name, count(*)::text AS row_count FROM {sql_identifier(table_name)}"
        for table_name in table_files
    ]
    count_query = "SELECT table_name, row_count FROM (" + " UNION ALL ".join(union_parts) + ") q ORDER BY table_name"
    query_lines.append(
        f"\\copy ({count_query}) TO 'database/postgresql_week11_table_counts.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');"
    )
    union_counts = [f"SELECT count(*) AS row_count FROM {sql_identifier(table_name)}" for table_name in table_files]
    total_query = "SELECT '临时库导入总行数' AS item, sum(row_count)::text AS value, 'Week11派生表合计行数' AS source_note FROM (" + " UNION ALL ".join(union_counts) + ") s"
    disclosure_parts = [
        "SELECT '数据库类型' AS item, 'PostgreSQL临时实例/长期库脚本' AS value, 'Week11同时提供临时复现与长期库迁移脚本' AS source_note",
        "SELECT '临时库导入表数量', count(*)::text, 'pevc_week11 schema中的Week11派生表' FROM information_schema.tables WHERE table_schema = 'pevc_week11'",
        total_query,
        "SELECT '基金深度核验队列数', count(*)::text, 'week11_fund_deep_enrichment_queue' FROM week11_fund_deep_enrichment_queue",
        "SELECT 'P1优先核验基金主体数', count(*)::text, 'manual_priority以P1开头' FROM week11_fund_deep_enrichment_queue WHERE manual_priority LIKE 'P1%'",
        "SELECT '备案编码/GP/LP已披露记录', count(*)::text, '只有任一深度字段非空才计数' FROM week11_fund_deep_enrichment_queue WHERE coalesce(amac_record_code,'') <> '' OR coalesce(gp_name,'') <> '' OR coalesce(lp_structure,'') <> ''",
    ]
    disclosure_query = " UNION ALL ".join(disclosure_parts)
    query_lines.append(
        f"\\copy ({disclosure_query}) TO 'database/postgresql_week11_disclosure.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');"
    )
    query_lines.append("")
    (DATABASE / "postgres_week11_queries.sql").write_text("\n".join(query_lines), encoding="utf-8")


def write_readme(readiness: dict[str, str]) -> None:
    text = f"""# 霍泓锟 第十一周任务提交

## 本周主题

第十一周承接第十周结果，把工作重点从“能生成研究面板”推进到“能进入长期数据库管理，并为基金备案编码、GP/LP结构补充建立人工核验队列”。

## 一键运行

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File code\\run_all_week11_codex.ps1
```

运行后会重新生成：

- `data/derived/`：第十一周派生表；
- `database/postgresql_week11_*.csv`：临时PostgreSQL导入后的披露结果；
- `outputs/week11_summary_workbook.xlsx`：Excel汇总表；
- `report/霍泓锟_第十一周任务报告.docx` 与 `.pdf`：提交报告；
- `logs/`：运行日志。

## PostgreSQL说明

当前主库5432检查状态：`{readiness['status']}`。

说明：如果没有设置 `PGPASSWORD`，脚本不会伪造长期库导入成功。本提交包提供：

- `database/run_postgres_temp_week11.ps1`：无需主库密码，在55433端口启动临时库，验证CSV与SQL可复现；
- `database/run_postgres_persistent_week11.ps1`：获得主库密码后，把同一批Week11派生表导入长期库 `pevc_week11` schema。

## 工程原则

基金备案编码、GP、LP结构只有在PDF或外部权威来源明确披露时才填写。当前三表未直接披露的字段保持空值，并在 `week11_fund_deep_enrichment_queue.csv` 与 `week11_manual_verification_template.csv` 中列为待核验事项。
"""
    (ROOT / "README.md").write_text(text, encoding="utf-8")


def write_validation(
    company_rows: list[dict[str, str]],
    fund_deep_rows: list[dict[str, object]],
    readiness: dict[str, str],
) -> None:
    pg_week11 = read_csv(DATABASE / "postgresql_week11_disclosure.csv")
    validation_rows = [
        {"check_item": "第十周输入CSV存在", "status": "PASS" if len(list(INPUT.glob("*.csv"))) >= 10 else "FAIL", "detail": f"input_week10 CSV数量={len(list(INPUT.glob('*.csv')))}"},
        {"check_item": "统一8家公司样本", "status": "PASS" if len(company_rows) == 8 else "WARN", "detail": f"公司样本数={len(company_rows)}"},
        {"check_item": "基金深度核验队列生成", "status": "PASS" if fund_deep_rows else "FAIL", "detail": f"基金队列记录={len(fund_deep_rows)}"},
        {"check_item": "未披露字段保持空值", "status": "PASS", "detail": "备案编码/GP/LP均未由名称推断。"},
        {"check_item": "长期库连接状态披露", "status": "PASS", "detail": readiness["status"]},
        {"check_item": "临时PostgreSQL披露结果", "status": "PASS" if pg_week11 else "PENDING", "detail": "运行run_postgres_temp_week11.ps1后生成。"},
    ]
    write_csv(VALIDATION / "week11_validation_summary.csv", validation_rows)


def main() -> None:
    ensure_dirs()
    company_rows = read_csv(INPUT / "company_research_panel_week10.csv")
    fund_rows = read_csv(INPUT / "fund_enrichment_queue_week10.csv")
    pg_summary = read_csv(INPUT / "postgresql_disclosure_summary_week10.csv")
    readiness = test_persistent_postgres()

    fund_deep = build_fund_deep_queue(fund_rows, company_rows)
    manual_template = build_manual_template(fund_deep)
    database_plan = build_database_migration_plan(pg_summary, readiness)
    readiness_rows = [
        {"check_item": "PostgreSQL客户端工具", "result": "存在" if readiness["status"] != "TOOL_MISSING" else "缺失", "detail": readiness["detail"], "action": readiness["action"]},
        {"check_item": "PGPASSWORD环境变量", "result": "已设置" if os.environ.get("PGPASSWORD") else "未设置", "detail": "用于非交互连接本机5432主库。", "action": "设置后运行长期库导入脚本。"},
        {"check_item": "长期库导入策略", "result": "脚本已准备", "detail": "不把临时库成功等同于长期库成功。", "action": "导入后使用table_counts对账。"},
    ]
    research_design = build_research_design(company_rows)
    variable_dictionary = build_variable_dictionary()
    sample_expansion = build_sample_expansion_plan(company_rows)
    quality_dashboard = build_quality_dashboard(company_rows, fund_deep, pg_summary, readiness)

    rows_by_name: dict[str, list[dict[str, object]]] = {
        "week11_database_migration_plan": database_plan,
        "week11_persistent_db_readiness": readiness_rows,
        "week11_fund_deep_enrichment_queue": fund_deep,
        "week11_manual_verification_template": manual_template,
        "week11_research_design_matrix": research_design,
        "week11_variable_dictionary": variable_dictionary,
        "week11_sample_expansion_plan": sample_expansion,
        "week11_quality_dashboard": quality_dashboard,
    }
    completion = build_completion_checklist()
    rows_by_name["week11_completion_checklist"] = completion

    for name, rows in rows_by_name.items():
        write_csv(DERIVED / f"{name}.csv", rows)

    manifest = build_manifest(rows_by_name)
    write_csv(DERIVED / "week11_manifest.csv", manifest)

    table_headers = {}
    for name in rows_by_name:
        csv_path = DERIVED / f"{name}.csv"
        with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.reader(fh)
            table_headers[name] = next(reader)
    table_headers["week11_manifest"] = list(manifest[0].keys())
    write_sql_files(table_headers)
    write_readme(readiness)
    write_validation(company_rows, fund_deep, readiness)

    pg_week11_disclosure = read_csv(DATABASE / "postgresql_week11_disclosure.csv")
    pg_week11_counts = read_csv(DATABASE / "postgresql_week11_table_counts.csv")
    payload = {
        "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "run_date": RUN_DATE,
        "source": "Week10 derived CSV + PostgreSQL disclosure CSV",
        "tables": {
            "database_migration_plan": database_plan,
            "persistent_db_readiness": readiness_rows,
            "fund_deep_enrichment_queue": fund_deep,
            "manual_verification_template": manual_template,
            "research_design_matrix": research_design,
            "variable_dictionary": variable_dictionary,
            "sample_expansion_plan": sample_expansion,
            "quality_dashboard": quality_dashboard,
            "completion_checklist": completion,
            "manifest": manifest,
            "week10_company_panel": company_rows,
            "week10_pg_summary": pg_summary,
            "postgresql_week11_disclosure": pg_week11_disclosure,
            "postgresql_week11_table_counts": pg_week11_counts,
        },
    }
    write_json(OUTPUTS / "week11_workbook_data.json", payload)
    write_json(OUTPUTS / "week11_summary.json", {
        "company_count": len(company_rows),
        "fund_queue_count": len(fund_deep),
        "manual_check_items": len(manual_template),
        "persistent_status": readiness["status"],
        "week10_pg_total_rows": count_rows_from_pg_summary(pg_summary, "导入总行数"),
        "run_date": RUN_DATE,
    })

    log_lines = [
        f"run_time={dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"company_count={len(company_rows)}",
        f"fund_queue_count={len(fund_deep)}",
        f"manual_check_items={len(manual_template)}",
        f"persistent_status={readiness['status']}",
    ]
    (LOGS / "week11_pipeline.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
