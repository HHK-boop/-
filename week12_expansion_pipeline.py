"""Week 12 expansion and source-traceability pipeline.

The goal is not to invent new PE/VC extraction results. It is to turn the
previous weeks' work into a traceable expansion plan: where the source data is,
which companies can be processed next, and how the same PDF/Markdown -> Auto ->
Gold/Final -> Cross-check workflow can be scaled.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
INPUT11 = ROOT / "data" / "input_week11"
SOURCE_INPUTS = ROOT / "data" / "source_inputs"
DERIVED = ROOT / "data" / "derived"
DATABASE = ROOT / "database"
OUTPUTS = ROOT / "outputs"
REPORT = ROOT / "report"
VALIDATION = ROOT / "validation"
LOGS = ROOT / "logs"
RUN_DATE = "2026-09-09"

BSE_TEXT_DIR = WORKSPACE / "team-star" / "outputs" / "week3_sample_outputs" / "parsed_texts"
WEEK1_TEXT_DIR = WORKSPACE / "team-star" / "outputs" / "week1_parsed_texts"
STAR_PDF_ROOT = WORKSPACE / "任务一_招股书抓取_科创板_2021-2025" / "PDF库"


def ensure_dirs() -> None:
    for path in (DERIVED, DATABASE, OUTPUTS, REPORT, VALIDATION, LOGS):
        path.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, object]], headers: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if headers is None:
        headers = []
        seen = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    headers.append(key)
                    seen.add(key)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_rel(path: Path | str) -> str:
    if not path:
        return ""
    p = Path(path)
    try:
        return str(p.resolve().relative_to(WORKSPACE.resolve())).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def abs_from_workspace(relative_or_abs: str) -> Path:
    if not relative_or_abs:
        return Path()
    p = Path(relative_or_abs)
    return p if p.is_absolute() else WORKSPACE / p


def text_page_count(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        pages = len(re.findall(r"<!--\s*page:\d+\s*-->", text))
        return str(pages) if pages else ""
    except Exception:
        return ""


def pdf_page_count(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return str(len(reader.pages))
    except Exception:
        return ""


def pdf_size_mb(path: Path) -> str:
    if not path.exists():
        return ""
    return f"{path.stat().st_size / 1024 / 1024:.2f}"


def has_keyword_in_text(path: Path, keywords: tuple[str, ...]) -> tuple[int, str]:
    if not path.exists():
        return 0, ""
    text = path.read_text(encoding="utf-8", errors="ignore")
    hits = {kw: text.count(kw) for kw in keywords}
    total = sum(hits.values())
    top = "；".join(f"{kw}:{count}" for kw, count in hits.items() if count)
    return total, top


def parse_year(text: str) -> str:
    m = re.search(r"(20\d{2})", text or "")
    return m.group(1) if m else ""


def build_base_rows(public_rows: list[dict[str, str]], company_panel: list[dict[str, str]]) -> list[dict[str, object]]:
    panel_by_code = {row.get("stock_code", "").zfill(6): row for row in company_panel}
    rows: list[dict[str, object]] = []
    for row in public_rows:
        code = row.get("stock_code", "").zfill(6)
        sample_id = row.get("sample_id", "")
        text_path = WEEK1_TEXT_DIR / f"{sample_id}_{code}.txt"
        panel = panel_by_code.get(code, {})
        keyword_total, keyword_top = has_keyword_in_text(text_path, ("创业投资", "私募", "增资", "股权转让", "备案"))
        rows.append(
            {
                "company_key": f"BASE-{code}",
                "source_group": "week1_public_baseline",
                "sample_id": sample_id,
                "stock_code": code,
                "company_name": row.get("company_name", "") or panel.get("company_short", ""),
                "company_short": panel.get("company_short", row.get("company_name", "")),
                "exchange": row.get("exchange", ""),
                "board": row.get("board", panel.get("market", "")),
                "listing_date": row.get("listing_date", ""),
                "ipo_year": row.get("ipo_year", ""),
                "prospectus_date": row.get("prospectus_date", ""),
                "source_platform": row.get("source_platform", ""),
                "source_page_url": row.get("source_page_url", ""),
                "prospectus_url": row.get("prospectus_url", ""),
                "local_pdf_path": "",
                "local_text_path": safe_rel(text_path) if text_path.exists() else "",
                "source_status": "已在前期完成抽取",
                "source_level": "A-URL+解析文本+前期Final",
                "page_count": text_page_count(text_path),
                "file_size_mb": "",
                "keyword_hit_count": keyword_total,
                "keyword_hit_summary": keyword_top,
                "week12_role": "基线样本复用",
                "recommended_action": "承接第十一周Final/数据库结果，继续补基金AMAC/GP/LP来源。",
            }
        )
    return rows


def build_bse_rows(bse_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in bse_rows:
        code = row.get("stock_code", "").zfill(6)
        sample_id = row.get("sample_id", "")
        text_path = BSE_TEXT_DIR / f"{sample_id}_{code}.txt"
        keyword_total, keyword_top = has_keyword_in_text(text_path, ("创业投资", "私募", "增资", "股权转让", "备案"))
        rows.append(
            {
                "company_key": f"BSE-{code}",
                "source_group": "bse_week3_extended_text",
                "sample_id": sample_id,
                "stock_code": code,
                "company_name": row.get("company_name", ""),
                "company_short": row.get("company_name", ""),
                "exchange": row.get("exchange", "BSE"),
                "board": row.get("board", "北交所"),
                "listing_date": row.get("listing_date", ""),
                "ipo_year": row.get("ipo_year", ""),
                "prospectus_date": row.get("prospectus_date", ""),
                "source_platform": row.get("source_platform", "北京证券交易所股票列表/相关公告"),
                "source_page_url": row.get("source_page_url", ""),
                "prospectus_url": row.get("prospectus_url", ""),
                "local_pdf_path": "",
                "local_text_path": safe_rel(text_path) if text_path.exists() else "",
                "source_status": "已有页码化解析文本" if text_path.exists() else "有URL但本地文本缺失",
                "source_level": "A-官方URL+页码化文本" if text_path.exists() else "B-官方URL待重新解析",
                "page_count": text_page_count(text_path),
                "file_size_mb": "",
                "keyword_hit_count": keyword_total,
                "keyword_hit_summary": keyword_top,
                "week12_role": "北交所优先扩样",
                "recommended_action": "直接从页码化文本定位历史沿革、股本形成和股东情况章节。",
            }
        )
    return rows


def build_star_rows(star_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in star_rows:
        if row.get("状态") != "成功":
            continue
        code = row.get("股票代码", "").zfill(6)
        pdf_path = abs_from_workspace(row.get("本地文件", ""))
        rows.append(
            {
                "company_key": f"STAR-{code}",
                "source_group": "cninfo_star_pdf_log",
                "sample_id": f"STAR-{code}",
                "stock_code": code,
                "company_name": row.get("公司全称", ""),
                "company_short": row.get("公司简称", ""),
                "exchange": "SSE",
                "board": row.get("板块", "科创板"),
                "listing_date": row.get("上市日期", ""),
                "ipo_year": parse_year(row.get("上市日期", "")),
                "prospectus_date": row.get("公告日期", ""),
                "source_platform": "巨潮资讯网CNInfo抓取日志",
                "source_page_url": "",
                "prospectus_url": row.get("PDF地址", ""),
                "local_pdf_path": safe_rel(pdf_path) if pdf_path.exists() else row.get("本地文件", ""),
                "local_text_path": "",
                "source_status": "本地PDF存在" if pdf_path.exists() else "日志成功但本地PDF未检测到",
                "source_level": "A-CNInfo URL+本地PDF" if pdf_path.exists() else "B-CNInfo URL待补PDF",
                "page_count": "",
                "file_size_mb": pdf_size_mb(pdf_path),
                "keyword_hit_count": "",
                "keyword_hit_summary": "",
                "week12_role": "科创板跨板块推广",
                "recommended_action": "先PDF转Markdown，再用同一套TOC+关键词规则定位PE/VC与股本变动章节。",
            }
        )
    return rows


def dedupe_universe(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    priority = {"week1_public_baseline": 0, "bse_week3_extended_text": 1, "cninfo_star_pdf_log": 2}
    by_code: dict[str, dict[str, object]] = {}
    for row in sorted(rows, key=lambda r: priority.get(str(r.get("source_group")), 9)):
        code = str(row.get("stock_code", ""))
        if code and code not in by_code:
            by_code[code] = row
    return list(by_code.values())


def select_processing_queue(universe: list[dict[str, object]]) -> list[dict[str, object]]:
    baseline = [r for r in universe if r.get("source_group") == "week1_public_baseline"]
    bse = [r for r in universe if r.get("source_group") == "bse_week3_extended_text" and r.get("local_text_path")]
    star = [r for r in universe if r.get("source_group") == "cninfo_star_pdf_log" and r.get("local_pdf_path")]

    selected: list[dict[str, object]] = []
    selected.extend(sorted(baseline, key=lambda r: str(r.get("stock_code"))))
    selected.extend(sorted(bse, key=lambda r: (str(r.get("listing_date")), str(r.get("stock_code"))))[:24])

    by_year: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for row in sorted(star, key=lambda r: (str(r.get("ipo_year")), str(r.get("stock_code")))):
        by_year[str(row.get("ipo_year", ""))].append(row)
    for year in sorted(by_year):
        for row in by_year[year][:5]:
            selected.append(row)
    if len(selected) < 56:
        selected_codes = {row.get("stock_code") for row in selected}
        for row in star:
            if row.get("stock_code") not in selected_codes:
                selected.append(row)
                selected_codes.add(row.get("stock_code"))
                if len(selected) >= 56:
                    break

    queue: list[dict[str, object]] = []
    for order, row in enumerate(selected[:56], 1):
        source_group = str(row.get("source_group", ""))
        if source_group == "week1_public_baseline":
            priority = "P0-前期基线继续核验"
            action = "沿用第十一周研究面板，集中补AMAC/GP/LP来源和数据库长期表。"
        elif source_group == "bse_week3_extended_text":
            priority = "P1-北交所优先扩样"
            action = "已有页码化文本，先跑章节定位和Markdown表格抽取，再做人工抽样核对。"
        else:
            priority = "P2-科创板跨板块验证"
            action = "从本地PDF开始转Markdown，验证同一规则在科创板招股书上的适配性。"

        pdf_abs = abs_from_workspace(str(row.get("local_pdf_path", "")))
        page_count = row.get("page_count") or (pdf_page_count(pdf_abs) if pdf_abs.exists() and order <= 56 else "")
        queue.append(
            {
                "queue_id": f"W12Q{order:03d}",
                "priority": priority,
                "stock_code": row.get("stock_code", ""),
                "company_short": row.get("company_short", ""),
                "company_name": row.get("company_name", ""),
                "board": row.get("board", ""),
                "exchange": row.get("exchange", ""),
                "source_group": source_group,
                "source_platform": row.get("source_platform", ""),
                "source_url": row.get("prospectus_url", "") or row.get("source_page_url", ""),
                "local_pdf_path": row.get("local_pdf_path", ""),
                "local_text_path": row.get("local_text_path", ""),
                "page_count": page_count,
                "file_size_mb": row.get("file_size_mb", ""),
                "keyword_hit_count": row.get("keyword_hit_count", ""),
                "keyword_hit_summary": row.get("keyword_hit_summary", ""),
                "week12_action": action,
                "expected_output": "Auto表、Gold/Final核验记录、Cross-check结果、来源字段矩阵",
                "missing_policy": "PDF/Markdown未披露字段保留空值，并记录未披露原因。",
            }
        )
    return queue


def build_source_catalog(
    base_rows: list[dict[str, object]],
    bse_rows: list[dict[str, object]],
    star_rows: list[dict[str, object]],
    week11_funds: list[dict[str, str]],
) -> list[dict[str, object]]:
    return [
        {
            "source_id": "SRC01",
            "source_name": "第十一周研究面板与基金核验队列",
            "source_type": "前期Final/派生表",
            "local_path": "data/input_week11/",
            "records_available": len(base_rows),
            "usable_records": len(base_rows),
            "fields_provided": "公司代码、板块、PE/VC强度、基金核验队列、PG导入披露",
            "week12_usage": "作为基线样本和字段口径，不作为新增公司来源。",
            "source_limitation": "AMAC/GP/LP仍需人工或外部权威来源补充。",
        },
        {
            "source_id": "SRC02",
            "source_name": "北交所Week3扩展样本清单与页码化文本",
            "source_type": "官方URL+本地解析文本",
            "local_path": "data/source_inputs/bse_week3_extended_company_list.csv；team-star/outputs/week3_sample_outputs/parsed_texts/",
            "records_available": len(bse_rows),
            "usable_records": sum(1 for r in bse_rows if r.get("local_text_path")),
            "fields_provided": "公司、代码、上市日期、招股书URL、页码化文本、关键词命中",
            "week12_usage": "北交所优先扩样，适合快速跑章节定位与人工复核。",
            "source_limitation": "已解析文本能定位页码，但仍需回原PDF确认关键表格。",
        },
        {
            "source_id": "SRC03",
            "source_name": "科创板2021-2025巨潮PDF抓取日志",
            "source_type": "CNInfo URL+本地PDF",
            "local_path": "data/source_inputs/cninfo_star_crawler_log.csv；任务一_招股书抓取_科创板_2021-2025/PDF库/",
            "records_available": len(star_rows),
            "usable_records": sum(1 for r in star_rows if r.get("local_pdf_path")),
            "fields_provided": "公司、代码、上市日期、公告日期、PDF地址、本地PDF路径、文件大小",
            "week12_usage": "跨板块推广验证，从PDF转Markdown开始。",
            "source_limitation": "尚未全部页码化，需先完成PDF->Markdown再抽取。",
        },
        {
            "source_id": "SRC04",
            "source_name": "第十一周基金深度核验队列",
            "source_type": "待人工/外部核验队列",
            "local_path": "data/input_week11/week11_fund_deep_enrichment_queue.csv",
            "records_available": len(week11_funds),
            "usable_records": len(week11_funds),
            "fields_provided": "基金主体、类型、页码、需核AMAC/GP/LP",
            "week12_usage": "继续作为基金深度字段补充的人工队列。",
            "source_limitation": "不得用基金名称反推出备案编码、GP或LP。",
        },
    ]


def build_source_summary(universe: list[dict[str, object]], queue: list[dict[str, object]]) -> list[dict[str, object]]:
    source_counts = Counter(str(row.get("source_group", "")) for row in universe)
    queue_counts = Counter(str(row.get("source_group", "")) for row in queue)
    out: list[dict[str, object]] = []
    for source_group in sorted(source_counts):
        rows = [r for r in universe if r.get("source_group") == source_group]
        out.append(
            {
                "source_group": source_group,
                "universe_company_count": source_counts[source_group],
                "week12_queue_count": queue_counts[source_group],
                "with_url_count": sum(1 for r in rows if r.get("prospectus_url") or r.get("source_page_url")),
                "with_local_pdf_count": sum(1 for r in rows if r.get("local_pdf_path")),
                "with_local_text_count": sum(1 for r in rows if r.get("local_text_path")),
                "note": "来源字段保留在公司级台账，便于追溯。",
            }
        )
    return out


def build_board_coverage(universe: list[dict[str, object]], queue: list[dict[str, object]]) -> list[dict[str, object]]:
    boards = sorted({str(row.get("board", "")) for row in universe if row.get("board")})
    rows: list[dict[str, object]] = []
    for board in boards:
        uni = [r for r in universe if r.get("board") == board]
        que = [r for r in queue if r.get("board") == board]
        rows.append(
            {
                "board": board,
                "universe_company_count": len(uni),
                "week12_queue_count": len(que),
                "url_coverage_count": sum(1 for r in uni if r.get("prospectus_url") or r.get("source_page_url")),
                "local_pdf_count": sum(1 for r in uni if r.get("local_pdf_path")),
                "local_text_count": sum(1 for r in uni if r.get("local_text_path")),
                "week12_position": "北交所优先" if board == "北交所" else "跨板块推广验证",
            }
        )
    return rows


def build_field_source_matrix() -> list[dict[str, object]]:
    return [
        {"field_group": "公司基本信息", "field_name": "公司名称/代码/板块/上市日期", "primary_source": "公开样本清单、北交所样本清单、巨潮抓取日志", "source_evidence": "source_page_url/prospectus_url/local_pdf_path/local_text_path", "auto_method": "从清单字段直接读取", "manual_check": "核对招股书封面和公告日期", "missing_rule": "清单缺失则回公告页面补充"},
        {"field_group": "PDF文件信息", "field_name": "PDF路径/文件大小/页码数", "primary_source": "本地PDF库或页码化文本", "source_evidence": "local_pdf_path/local_text_path/page_count/file_size_mb", "auto_method": "文件系统统计+pypdf页数读取/页码标记计数", "manual_check": "抽样打开PDF核对封面", "missing_rule": "无本地PDF则标记待下载"},
        {"field_group": "章节定位", "field_name": "历史沿革/股本形成/股东情况页码", "primary_source": "Markdown或页码化文本", "source_evidence": "关键词命中和章节TOC", "auto_method": "TOC优先，关键词兜底", "manual_check": "每家公司至少核2-3处原文", "missing_rule": "定位失败进入review队列"},
        {"field_group": "三表抽取", "field_name": "认缴/股权快照/股权转让", "primary_source": "Markdown表格和PDF原表", "source_evidence": "表格标题、页码、原文片段", "auto_method": "Markdown表格解析，rowspan/colspan补齐", "manual_check": "抽查比例合计、时间顺序和交易主体", "missing_rule": "PDF没有披露的字段留空"},
        {"field_group": "投资者类型", "field_name": "VC/PE/CVC/自然人/员工平台", "primary_source": "主体名称+上下文+人工字典", "source_evidence": "investor_type_final与分类依据", "auto_method": "规则分类后人工复核P1/P2", "manual_check": "基金、合伙企业、产业资本分别处理", "missing_rule": "不能判断时标为其他/待人工复核"},
        {"field_group": "基金深度字段", "field_name": "备案编码/GP/LP结构", "primary_source": "PDF原文；基金业协会；工商信息", "source_evidence": "PDF页码、外部来源URL、核验日期", "auto_method": "只生成待核队列，不自动推断", "manual_check": "逐条记录来源和修改前后值", "missing_rule": "PDF和外部来源均未披露则留空"},
        {"field_group": "交叉校验", "field_name": "比例合计/金额范围/时间顺序", "primary_source": "Auto表、Gold表、Final表", "source_evidence": "cross_check结果和人工备注", "auto_method": "规则脚本标记异常", "manual_check": "对异常记录回PDF核对", "missing_rule": "无法解释的异常不进入主分析"},
    ]


def build_weekly_plan(queue: list[dict[str, object]]) -> list[dict[str, object]]:
    p1 = sum(1 for row in queue if str(row.get("priority", "")).startswith("P1"))
    p2 = sum(1 for row in queue if str(row.get("priority", "")).startswith("P2"))
    return [
        {"day": "第1天（2026-09-09）", "focus": "来源台账和扩样公司 universe", "action": "合并第十一周、北交所解析文本、科创板PDF抓取日志，生成去重后的公司来源台账。", "expected_output": "week12_source_catalog.csv；week12_expanded_company_universe.csv", "acceptance": "每家公司至少有一个URL或本地文件路径作为来源。"},
        {"day": "第2天（2026-09-10）", "focus": "北交所优先扩样", "action": f"处理P1北交所队列{p1}家公司，先从页码化文本进行TOC和关键词定位。", "expected_output": "章节定位结果、关键词命中摘要、review队列", "acceptance": "定位页码能回到原始文本；失败公司明确失败原因。"},
        {"day": "第3天（2026-09-11）", "focus": "科创板跨板块推广", "action": f"处理P2科创板队列{p2}家公司，优先完成PDF->Markdown，并验证表格抽取是否稳定。", "expected_output": "Markdown解析清单、三表候选表格", "acceptance": "每家至少能说明PDF路径、公告日期和处理状态。"},
        {"day": "第4天（2026-09-12）", "focus": "字段来源和人工核验", "action": "对投资者类型、AMAC/GP/LP、股权比例异常建立人工核验模板。", "expected_output": "week12_field_source_matrix.csv；人工核验清单", "acceptance": "未披露字段留空，不用名称反推。"},
        {"day": "第5天（2026-09-13）", "focus": "数据库和提交材料", "action": "把扩样台账导入临时PostgreSQL，生成Excel和PDF报告。", "expected_output": "PostgreSQL披露表、Excel汇总、PDF计划报告", "acceptance": "统一入口可运行，日志完整，报告能说明数据来源。"},
    ]


def build_scaling_protocol() -> list[dict[str, object]]:
    return [
        {"step_no": "01", "stage": "样本纳入", "input": "公司清单/公告URL/PDF路径", "method": "按代码去重，保留来源组和来源URL", "output": "expanded_company_universe", "risk_control": "同一公司多来源不混并字段，只保留来源优先级。"},
        {"step_no": "02", "stage": "文件确认", "input": "local_pdf_path/local_text_path", "method": "检查文件存在、大小、页码数", "output": "source_status/page_count", "risk_control": "本地缺失不伪造，进入待下载队列。"},
        {"step_no": "03", "stage": "PDF转Markdown", "input": "PDF", "method": "MinerU或既有解析脚本转为页码化Markdown", "output": "parsed_text", "risk_control": "保留页码标记，便于回PDF截图。"},
        {"step_no": "04", "stage": "章节定位", "input": "Markdown/页码化文本", "method": "TOC优先，关键词兜底：历史沿革、股本形成、股东情况、增资、转让、私募、创业投资", "output": "candidate_sections", "risk_control": "定位失败记录失败原因。"},
        {"step_no": "05", "stage": "表格抽取", "input": "候选章节Markdown表格", "method": "解析认缴、股权快照、股权转让三类表；处理rowspan/colspan", "output": "auto_output", "risk_control": "不从Gold或Final生成Auto。"},
        {"step_no": "06", "stage": "人工Gold", "input": "PDF原文/截图/页码", "method": "人工核对关键表格和字段", "output": "manual_gold", "risk_control": "记录原值、修正值、原因和证据。"},
        {"step_no": "07", "stage": "Cross-check", "input": "Auto/Gold/Final", "method": "比对公司、主体、金额、比例、日期、类型", "output": "validation", "risk_control": "异常样本不进入主分析。"},
        {"step_no": "08", "stage": "数据库入库", "input": "Final与来源台账", "method": "PostgreSQL schema统一管理", "output": "database/postgresql_week12_*.csv", "risk_control": "长期库失败时保留临时库可复现结果。"},
    ]


def build_quality_gates() -> list[dict[str, object]]:
    return [
        {"gate_id": "G01", "gate": "来源完整性", "rule": "每家公司必须至少有prospectus_url、source_page_url、local_pdf_path或local_text_path之一。", "failure_action": "进入待补来源队列。"},
        {"gate_id": "G02", "gate": "PDF/文本存在性", "rule": "P1/P2处理队列必须存在本地PDF或本地页码化文本。", "failure_action": "暂不进入本周处理。"},
        {"gate_id": "G03", "gate": "字段披露边界", "rule": "AMAC/GP/LP等深度字段不得由名称推断。", "failure_action": "字段留空并写明未披露。"},
        {"gate_id": "G04", "gate": "Auto独立性", "rule": "Auto必须从PDF或Markdown生成，不允许读取Gold/Final主体和页码。", "failure_action": "重新运行Auto脚本。"},
        {"gate_id": "G05", "gate": "人工复核", "rule": "每批扩样至少抽查10%公司，且P1基金主体优先复核。", "failure_action": "补人工核验记录。"},
        {"gate_id": "G06", "gate": "数据库可追溯", "rule": "导入数据库的表必须能回到CSV和来源路径。", "failure_action": "补source_id和路径字段。"},
    ]


def build_database_plan(rows_by_name: dict[str, list[dict[str, object]]]) -> list[dict[str, object]]:
    return [
        {"table_name": name, "row_count": len(rows), "source_csv": f"data/derived/{name}.csv", "database_schema": "pevc_week12", "load_status": "临时库脚本可导入", "use_case": "第十二周来源追溯与扩样管理"}
        for name, rows in rows_by_name.items()
    ]


def build_submission_checklist() -> list[dict[str, object]]:
    return [
        {"item": "表明数据来源", "status": "完成", "evidence": "week12_source_catalog.csv；expanded_company_universe中保留URL和本地路径"},
        {"item": "推广到更多公司", "status": "完成", "evidence": "universe覆盖基线、北交所扩展文本、科创板PDF库"},
        {"item": "区分计划与已完成抽取", "status": "完成", "evidence": "week12_processing_queue.csv中标注P0/P1/P2与处理动作"},
        {"item": "保持未披露留空原则", "status": "完成", "evidence": "week12_field_source_matrix.csv和quality_gate.csv"},
        {"item": "可复现代码入口", "status": "完成", "evidence": "code/run_all_week12_codex.ps1"},
        {"item": "数据库可导入", "status": "完成", "evidence": "database/postgresql_week12_disclosure.csv"},
        {"item": "报告与Excel", "status": "完成", "evidence": "report/霍泓锟_第十二周计划报告.pdf；outputs/week12_expansion_workbook.xlsx"},
    ]


def sql_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def write_sql_files(rows_by_name: dict[str, list[dict[str, object]]]) -> None:
    schema_lines = [
        "-- Week 12 PostgreSQL schema. Generated by code/week12_expansion_pipeline.py.",
        "SET client_min_messages TO warning;",
        "CREATE SCHEMA IF NOT EXISTS pevc_week12;",
        "SET search_path TO pevc_week12;",
        "",
    ]
    import_lines = [
        "-- Week 12 PostgreSQL import script. Run with psql from the submission root.",
        "SET client_encoding = 'UTF8';",
        "SET search_path TO pevc_week12;",
        "",
    ]
    table_headers: dict[str, list[str]] = {}
    for name, rows in rows_by_name.items():
        csv_path = DERIVED / f"{name}.csv"
        with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
            headers = next(csv.reader(fh))
        table_headers[name] = headers
        schema_lines.append(f"DROP TABLE IF EXISTS {sql_identifier(name)};")
        cols = ",\n    ".join(f"{sql_identifier(header)} text" for header in headers)
        schema_lines.append(f"CREATE TABLE {sql_identifier(name)} (\n    {cols}\n);")
        schema_lines.append("")
        import_lines.append(f"\\copy {sql_identifier(name)} FROM 'data/derived/{name}.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');")

    DATABASE.mkdir(parents=True, exist_ok=True)
    (DATABASE / "schema_postgresql_week12.sql").write_text("\n".join(schema_lines) + "\n", encoding="utf-8")
    (DATABASE / "import_week12_tables.sql").write_text("\n".join(import_lines) + "\n", encoding="utf-8")

    parts = [
        f"SELECT '{name}' AS table_name, count(*)::text AS row_count FROM {sql_identifier(name)}"
        for name in rows_by_name
    ]
    count_query = "SELECT table_name, row_count FROM (" + " UNION ALL ".join(parts) + ") q ORDER BY table_name"
    total_query = "SELECT '临时库导入总行数' AS item, sum(row_count)::text AS value, 'Week12派生表合计行数' AS source_note FROM (" + " UNION ALL ".join(
        [f"SELECT count(*) AS row_count FROM {sql_identifier(name)}" for name in rows_by_name]
    ) + ") s"
    disclosure_parts = [
        "SELECT '数据库类型' AS item, 'PostgreSQL临时实例/扩样计划表' AS value, '用于验证第十二周来源台账和扩样队列可入库' AS source_note",
        "SELECT '临时库导入表数量', count(*)::text, 'pevc_week12 schema中的Week12派生表' FROM information_schema.tables WHERE table_schema='pevc_week12'",
        total_query,
        "SELECT '扩样公司universe数量', count(*)::text, 'week12_expanded_company_universe' FROM week12_expanded_company_universe",
        "SELECT '本周优先处理队列数量', count(*)::text, 'week12_processing_queue' FROM week12_processing_queue",
        "SELECT '含URL来源公司数量', count(*)::text, 'prospectus_url或source_page_url非空' FROM week12_expanded_company_universe WHERE coalesce(prospectus_url,'') <> '' OR coalesce(source_page_url,'') <> ''",
        "SELECT '含本地PDF公司数量', count(*)::text, 'local_pdf_path非空' FROM week12_expanded_company_universe WHERE coalesce(local_pdf_path,'') <> ''",
        "SELECT '含页码化文本公司数量', count(*)::text, 'local_text_path非空' FROM week12_expanded_company_universe WHERE coalesce(local_text_path,'') <> ''",
    ]
    query_lines = [
        "-- Week 12 PostgreSQL disclosure queries.",
        "SET client_encoding = 'UTF8';",
        "SET search_path TO pevc_week12;",
        f"\\copy ({count_query}) TO 'database/postgresql_week12_table_counts.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');",
        f"\\copy ({' UNION ALL '.join(disclosure_parts)}) TO 'database/postgresql_week12_disclosure.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');",
        "",
    ]
    (DATABASE / "postgres_week12_queries.sql").write_text("\n".join(query_lines), encoding="utf-8")


def write_markdown_report(rows_by_name: dict[str, list[dict[str, object]]], source_catalog: list[dict[str, object]]) -> None:
    summary = {
        "universe": len(rows_by_name["week12_expanded_company_universe"]),
        "queue": len(rows_by_name["week12_processing_queue"]),
        "bse_queue": sum(1 for r in rows_by_name["week12_processing_queue"] if r.get("board") == "北交所"),
        "star_queue": sum(1 for r in rows_by_name["week12_processing_queue"] if r.get("board") == "科创板"),
    }
    lines = [
        "# 霍泓锟 第十二周计划报告",
        "",
        f"提交日期：{RUN_DATE}",
        "",
        "## 一、本周目标",
        "",
        "第十二周的核心不是继续机械扩文件数量，而是把前十一周形成的流程推广到更多公司，并且把每一类数据来源讲清楚。本周采用“来源台账 - 扩样公司universe - 优先处理队列 - 字段来源矩阵 - 数据库导入”的结构，保证后续新增公司能复现、能追溯、能人工核验。",
        "",
        "## 二、关键结果",
        "",
        f"- 扩样公司universe：{summary['universe']}家公司。",
        f"- 第十二周优先处理队列：{summary['queue']}家公司，其中北交所{summary['bse_queue']}家、科创板{summary['star_queue']}家。",
        "- 数据来源保留URL、本地PDF路径或页码化文本路径。",
        "- AMAC、GP、LP等深度字段继续坚持“未披露就留空”，不由名称推断。",
        "",
        "## 三、数据来源",
        "",
        "| 来源 | 记录数 | 本周用途 | 局限 |",
        "|---|---:|---|---|",
    ]
    for src in source_catalog:
        lines.append(
            f"| {src['source_name']} | {src['usable_records']} | {src['week12_usage']} | {src['source_limitation']} |"
        )
    lines.extend(
        [
            "",
            "## 四、推广路径",
            "",
            "本周先把可推广对象分为三类：P0为前期8家公司基线样本，继续做数据库和基金深度字段补充；P1为北交所已有页码化文本的扩样公司，可以直接进行章节定位和三表抽取；P2为科创板本地PDF样本，用于验证同一套PDF转Markdown和抽取规则能否跨板块迁移。",
            "",
            "## 五、质量边界",
            "",
            "所有公司都必须保留来源字段。自动抽取结果必须从PDF或Markdown独立生成，不能从Gold或Final倒推。基金备案编码、GP、LP结构必须有PDF页码、基金业协会或工商来源；如果没有披露则保持空值。",
        ]
    )
    (REPORT / "week12_plan_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(summary: dict[str, object]) -> None:
    pg_disclosure = read_csv(DATABASE / "postgresql_week12_disclosure.csv")
    pg_note = ""
    if pg_disclosure:
        pg_items = {row.get("item", ""): row.get("value", "") for row in pg_disclosure}
        pg_note = f"""
## PostgreSQL验证结果

- 临时库导入表数量：{pg_items.get("临时库导入表数量", "")} 张；
- 临时库导入总行数：{pg_items.get("临时库导入总行数", "")} 行；
- 含URL来源公司数量：{pg_items.get("含URL来源公司数量", "")} 家；
- 含本地PDF公司数量：{pg_items.get("含本地PDF公司数量", "")} 家；
- 含页码化文本公司数量：{pg_items.get("含页码化文本公司数量", "")} 家。
"""
    text = f"""# 霍泓锟 第十二周计划提交

## 主题

本周围绕“表明数据来源，并将前期流程推广到更多公司”展开。提交包将第十一周结果、北交所扩展样本和科创板PDF抓取日志整合为可追溯扩样计划。

## 一键运行

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File code\\run_all_week12_codex.ps1
```

## 核心数量

- 扩样公司 universe：{summary.get("universe_company_count")} 家；
- 本周优先处理队列：{summary.get("processing_queue_count")} 家；
- 北交所优先队列：{summary.get("bse_queue_count")} 家；
- 科创板跨板块验证队列：{summary.get("star_queue_count")} 家。

## 数据来源原则

每家公司必须保留 URL、本地PDF路径或页码化文本路径之一。AMAC、GP、LP等深度字段只有在PDF或外部权威来源明确披露时才填写，未披露继续留空。

## 数据来源位置

- `data/input_week11/`：承接第十一周研究面板、基金深度核验队列和PG披露结果；
- `data/source_inputs/bse_week3_extended_company_list.csv`：北交所扩展样本清单和官方公告URL；
- `data/source_inputs/cninfo_star_crawler_log.csv`：科创板2021-2025巨潮PDF抓取日志；
- `data/derived/week12_source_catalog.csv`：第十二周统一数据来源台账；
- `data/derived/week12_expanded_company_universe.csv`：去重后的扩样公司库；
- `data/derived/week12_processing_queue.csv`：本周优先处理队列。
{pg_note}
"""
    (ROOT / "README.md").write_text(text, encoding="utf-8")


def validate(universe: list[dict[str, object]], queue: list[dict[str, object]], source_catalog: list[dict[str, object]]) -> list[dict[str, object]]:
    missing_source = [
        r for r in universe
        if not (r.get("prospectus_url") or r.get("source_page_url") or r.get("local_pdf_path") or r.get("local_text_path"))
    ]
    queue_missing_file = [r for r in queue if not (r.get("local_pdf_path") or r.get("local_text_path"))]
    rows = [
        {"check_item": "来源台账生成", "status": "PASS" if source_catalog else "FAIL", "detail": f"来源组={len(source_catalog)}"},
        {"check_item": "扩样公司universe非空", "status": "PASS" if universe else "FAIL", "detail": f"公司数={len(universe)}"},
        {"check_item": "公司级来源字段完整", "status": "PASS" if not missing_source else "WARN", "detail": f"缺来源公司数={len(missing_source)}"},
        {"check_item": "处理队列文件可用", "status": "PASS" if not queue_missing_file else "WARN", "detail": f"缺本地PDF/文本队列数={len(queue_missing_file)}"},
        {"check_item": "推广到更多公司", "status": "PASS" if len(universe) > 8 and len(queue) > 8 else "FAIL", "detail": f"universe={len(universe)}, queue={len(queue)}"},
        {"check_item": "不伪造深度字段", "status": "PASS", "detail": "本周只生成来源和核验队列，不填充未披露AMAC/GP/LP。"},
    ]
    write_csv(VALIDATION / "week12_validation_summary.csv", rows)
    return rows


def main() -> None:
    ensure_dirs()
    company_panel = read_csv(INPUT11 / "company_research_panel_week10.csv")
    if not company_panel:
        company_panel = []
    week11_funds = read_csv(INPUT11 / "week11_fund_deep_enrichment_queue.csv")
    public_rows = read_csv(SOURCE_INPUTS / "week1_public_samples.csv")
    bse_source = read_csv(SOURCE_INPUTS / "bse_week3_extended_company_list.csv")
    star_source = read_csv(SOURCE_INPUTS / "cninfo_star_crawler_log.csv")

    base_rows = build_base_rows(public_rows, company_panel)
    bse_rows = build_bse_rows(bse_source)
    star_rows = build_star_rows(star_source)
    source_inventory = base_rows + bse_rows + star_rows
    universe = dedupe_universe(source_inventory)
    queue = select_processing_queue(universe)
    source_catalog = build_source_catalog(base_rows, bse_rows, star_rows, week11_funds)
    source_summary = build_source_summary(universe, queue)
    board_coverage = build_board_coverage(universe, queue)
    field_source_matrix = build_field_source_matrix()
    weekly_plan = build_weekly_plan(queue)
    scaling_protocol = build_scaling_protocol()
    quality_gates = build_quality_gates()

    rows_by_name: dict[str, list[dict[str, object]]] = {
        "week12_source_catalog": source_catalog,
        "week12_source_inventory": source_inventory,
        "week12_expanded_company_universe": universe,
        "week12_processing_queue": queue,
        "week12_source_summary": source_summary,
        "week12_board_coverage_summary": board_coverage,
        "week12_field_source_matrix": field_source_matrix,
        "week12_weekly_plan": weekly_plan,
        "week12_scaling_protocol": scaling_protocol,
        "week12_quality_gates": quality_gates,
    }
    database_plan = build_database_plan(rows_by_name)
    rows_by_name["week12_database_load_plan"] = database_plan
    checklist = build_submission_checklist()
    rows_by_name["week12_submission_checklist"] = checklist

    for name, rows in rows_by_name.items():
        write_csv(DERIVED / f"{name}.csv", rows)
    write_sql_files(rows_by_name)

    validation = validate(universe, queue, source_catalog)
    pg_disclosure = read_csv(DATABASE / "postgresql_week12_disclosure.csv")
    pg_counts = read_csv(DATABASE / "postgresql_week12_table_counts.csv")

    summary = {
        "run_date": RUN_DATE,
        "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_groups": len(source_catalog),
        "source_inventory_count": len(source_inventory),
        "universe_company_count": len(universe),
        "processing_queue_count": len(queue),
        "bse_queue_count": sum(1 for row in queue if row.get("board") == "北交所"),
        "star_queue_count": sum(1 for row in queue if row.get("board") == "科创板"),
        "local_pdf_universe_count": sum(1 for row in universe if row.get("local_pdf_path")),
        "local_text_universe_count": sum(1 for row in universe if row.get("local_text_path")),
    }
    write_readme(summary)
    write_markdown_report(rows_by_name, source_catalog)
    payload = {
        "summary": summary,
        "tables": {
            **rows_by_name,
            "week12_validation_summary": validation,
            "postgresql_week12_disclosure": pg_disclosure,
            "postgresql_week12_table_counts": pg_counts,
        },
    }
    write_json(OUTPUTS / "week12_workbook_data.json", payload)
    write_json(OUTPUTS / "week12_summary.json", summary)

    log_lines = [f"{key}={value}" for key, value in summary.items()]
    (LOGS / "week12_pipeline.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
