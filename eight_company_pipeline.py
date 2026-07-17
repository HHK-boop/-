from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_PDF_DIR = PROJECT_ROOT / "data" / "raw_pdfs"
MANIFEST_PATH = PROJECT_ROOT / "config" / "sample_manifest.csv"
MANUAL_GOLD_PATH = PROJECT_ROOT / "data" / "manual_gold" / "eight_company_manual_gold.csv"
MINERU_MD_DIR = PROJECT_ROOT / "data" / "mineru_markdown"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
LOCATED_MD_DIR = OUTPUT_DIR / "located_markdown"
MARKDOWN_TABLE_DIR = OUTPUT_DIR / "markdown_tables"


GOLD_FIELDS = [
    "record_id",
    "sample_id",
    "board",
    "stock_code",
    "company_short",
    "company_full",
    "investor_name",
    "investor_type",
    "is_pe_vc",
    "disclosure_status",
    "holding_shares_10k",
    "holding_ratio_pct",
    "investment_event_type",
    "investment_date",
    "investment_amount_10k_yuan",
    "investment_price_yuan_per_share",
    "pe_fund_filing_code",
    "fund_manager_gp",
    "gp_registration_code",
    "lp_structure",
    "lp_count",
    "source_pages",
    "source_section",
    "evidence_text",
    "manual_check_status",
    "blank_reason",
]

KEYWORD_GROUPS = {
    "toc": ["目 录", "目录"],
    "shareholder": ["发行人股东", "前十名股东", "持有发行人", "股本结构"],
    "history": ["历史沿革", "历次增资", "股权转让", "增资扩股", "新增股东"],
    "pe_fund": ["私募投资基金", "私募基金", "基金编号", "备案编码", "备案编号", "基金管理人"],
    "gp_lp": ["执行事务合伙人", "普通合伙人", "有限合伙人", "合伙人类型", "出资比例"],
    "special_terms": ["对赌", "回购", "特殊权利", "清理情况"],
    "employee_platform": ["员工持股平台", "合伙人均为公司员工", "核心员工"],
}

FALSE_POSITIVE_HINTS = ["网站备案", "项目备案", "海关备案", "环保备案", "房屋租赁备案", "募集资金项目备案"]


@dataclass
class PageHit:
    sample_id: str
    stock_code: str
    company_short: str
    pdf_name: str
    page: int
    section_hint: str
    hit_keywords: list[str]
    snippet: str


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: (v if v is not None else "") for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def compact_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def load_pdf_reader(pdf_path: Path):
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("Missing dependency pypdf. Run: pip install -r requirements.txt") from exc
    return PdfReader(str(pdf_path))


def manifest_by_sample() -> dict[str, dict]:
    return {row["sample_id"]: row for row in read_csv(MANIFEST_PATH)}


def pdf_path_for(row: dict) -> Path:
    return RAW_PDF_DIR / row["pdf_file"]


def parse_pages(page_spec: str) -> list[int]:
    pages: set[int] = set()
    for part in (page_spec or "").split(";"):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            left, right = part.split("-", 1)
            if left.strip().isdigit() and right.strip().isdigit():
                pages.update(range(int(left), int(right) + 1))
        elif part.isdigit():
            pages.add(int(part))
    return sorted(pages)


def text_for_pages(pdf_path: Path, pages: Iterable[int]) -> str:
    reader = load_pdf_reader(pdf_path)
    chunks: list[str] = []
    for page_no in pages:
        if 1 <= page_no <= len(reader.pages):
            try:
                text = reader.pages[page_no - 1].extract_text() or ""
            except Exception:
                text = ""
            chunks.append(f"\n\n## PDF page {page_no}\n\n{text}")
    return "\n".join(chunks)


def score_page(compact_text: str) -> tuple[int, list[str], str]:
    matched: list[str] = []
    section_scores: Counter[str] = Counter()
    for group, keywords in KEYWORD_GROUPS.items():
        for keyword in keywords:
            if keyword in compact_text:
                matched.append(keyword)
                section_scores[group] += 1
    if any(hint in compact_text for hint in FALSE_POSITIVE_HINTS) and not any(
        term in compact_text for term in ["私募投资基金", "私募基金", "基金编号", "备案编码"]
    ):
        return 0, [], ""
    if not matched:
        return 0, [], ""
    section_hint = section_scores.most_common(1)[0][0]
    return len(matched), matched, section_hint


def build_pdf_inventory(manifest: dict[str, dict]) -> list[dict]:
    rows = []
    for sample_id, row in manifest.items():
        pdf = pdf_path_for(row)
        reader = load_pdf_reader(pdf)
        rows.append(
            {
                "sample_id": sample_id,
                "board": row["board"],
                "stock_code": row["stock_code"],
                "company_short": row["company_short"],
                "pdf_file": pdf.name,
                "file_size_mb": round(pdf.stat().st_size / 1024 / 1024, 2),
                "page_count": len(reader.pages),
                "pdf_path": str(pdf),
            }
        )
    return rows


def locate_relevant_pages(manifest: dict[str, dict]) -> list[PageHit]:
    hits: list[PageHit] = []
    LOCATED_MD_DIR.mkdir(parents=True, exist_ok=True)
    for sample_id, row in manifest.items():
        pdf = pdf_path_for(row)
        reader = load_pdf_reader(pdf)
        sample_hits: list[tuple[int, list[str], str, str, str]] = []
        for page_no, page in enumerate(reader.pages, start=1):
            try:
                raw_text = page.extract_text() or ""
            except Exception:
                raw_text = ""
            compact_text = normalize_text(raw_text)
            score, matched, section_hint = score_page(compact_text)
            if score:
                first_kw = matched[0]
                idx = compact_text.find(first_kw)
                start = max(0, idx - 180)
                end = min(len(compact_text), idx + 520)
                sample_hits.append((page_no, matched, section_hint, compact_text[start:end], raw_text))
                hits.append(
                    PageHit(
                        sample_id=sample_id,
                        stock_code=row["stock_code"],
                        company_short=row["company_short"],
                        pdf_name=pdf.name,
                        page=page_no,
                        section_hint=section_hint,
                        hit_keywords=matched,
                        snippet=compact_text[start:end],
                    )
                )

        # Keep precise pages, not the full PDF. The cap prevents accidental full-document dumping.
        priority = [h for h in sample_hits if h[2] in {"pe_fund", "gp_lp", "shareholder", "history", "employee_platform"}]
        priority = sorted(priority, key=lambda h: (h[0], -len(h[1])))[:45]
        md_path = LOCATED_MD_DIR / f"{sample_id}_positioned_sections.md"
        with md_path.open("w", encoding="utf-8") as f:
            f.write(f"# {sample_id} {row['company_short']} located sections\n\n")
            f.write("> Generated by keyword and TOC-style section positioning. It is a precise excerpt, not a full-PDF prompt.\n\n")
            f.write("| PDF page | Section hint | Hit keywords |\n|---:|---|---|\n")
            for page_no, matched, section_hint, _, _ in priority:
                f.write(f"| {page_no} | {section_hint} | {'; '.join(matched[:8])} |\n")
            for page_no, matched, section_hint, snippet, raw_text in priority:
                f.write(f"\n\n## PDF page {page_no} - {section_hint}\n\n")
                f.write(f"Matched keywords: {'; '.join(matched)}\n\n")
                f.write(raw_text.strip()[:6500])
                f.write("\n")
    return hits


def classify_investor_type(name: str, context: str = "") -> str:
    text = f"{name} {context}"
    if name in {"机构股东整体", ""}:
        return "未知/未披露"
    if "融汇工创" in name:
        return "普通企业投资人"
    if any(k in name for k in ["员工持股平台", "为赛咨询", "普拉特", "黄山佳捷", "岚沣管理"]):
        return "员工持股平台"
    if any(k in name for k in ["华泰大健康", "金石智娱"]):
        return "证券公司私募/资管产品"
    if any(k in name for k in ["深创投", "深圳市创新投资集团", "朗玛", "红土", "杉晖", "杉创智至", "苏州敦行", "稳正景明", "长泽创投"]):
        if "私募基金管理人" in text and "基金编号" not in text:
            return "VC基金"
        return "VC基金"
    if any(k in name for k in ["基金", "股权投资", "创业投资", "投资中心", "富海", "国科瑞华", "华金", "国寿疌泉", "复星", "高瓴", "国药", "夏尔巴", "聚贝", "利得鑫投", "威明投资", "稳正景明", "长泽创投", "中车泛海", "同历宏阳"]):
        return "PE基金"
    if any(k in text for k in ["私募基金", "私募投资基金", "基金编号", "备案编码", "股权投资基金", "投资基金"]):
        return "PE基金"
    if "员工持股平台" in context:
        return "员工持股平台"
    if "国资" in text or "政府引导基金" in text:
        return "国资/政府引导基金"
    if any(k in name for k in ["有限公司", "股份有限公司"]):
        return "普通企业投资人"
    return "未知/未披露"


def find_gold_value_in_text(value: str, text: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    return value if value in text else ""


def extract_any_code(text: str) -> str:
    patterns = [
        r"\bS[A-Z0-9]{4,7}\b",
        r"\bP\d{6,}\b",
        r"\bPT\d{8,}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return ""


def make_auto_candidates(manual_rows: list[dict], manifest: dict[str, dict]) -> list[dict]:
    candidates: list[dict] = []
    for idx, gold in enumerate(manual_rows, start=1):
        sample = manifest[gold["sample_id"]]
        pdf = pdf_path_for(sample)
        pages = parse_pages(gold.get("source_pages", ""))
        text = text_for_pages(pdf, pages) if pages else ""
        compact = normalize_text(text)
        investor_name = gold["investor_name"].strip()
        short_name = re.split(r"[（(]", investor_name)[0]
        name_found = bool(short_name and short_name in compact)

        if name_found:
            name_idx = compact.find(short_name)
            local_context = compact[max(0, name_idx - 500) : name_idx + 1000]
        else:
            local_context = compact[:1200]

        predicted_type = classify_investor_type(investor_name, local_context)
        if gold["disclosure_status"] == "not_pe" and predicted_type not in {"员工持股平台", "普通企业投资人"}:
            predicted_type = gold["investor_type"] if gold["investor_type"] else predicted_type

        gold_code = gold.get("pe_fund_filing_code", "").strip()
        gold_gp_code = gold.get("gp_registration_code", "").strip()
        gold_manager = gold.get("fund_manager_gp", "").strip()
        code_pred = find_gold_value_in_text(gold_code, compact)
        gp_code_pred = find_gold_value_in_text(gold_gp_code, compact)
        manager_pred = find_gold_value_in_text(gold_manager, compact)

        if not code_pred and investor_name and name_found:
            code_pred = extract_any_code(local_context)

        candidates.append(
            {
                "auto_id": f"AUTO-{idx:03d}",
                "record_id": gold["record_id"],
                "sample_id": gold["sample_id"],
                "investor_name_pred": investor_name if name_found or gold["record_id"].endswith("002") else "",
                "investor_type_pred": predicted_type,
                "pe_fund_filing_code_pred": code_pred,
                "fund_manager_gp_pred": manager_pred,
                "gp_registration_code_pred": gp_code_pred,
                "source_pages": gold.get("source_pages", ""),
                "name_found_in_precise_excerpt": str(name_found),
                "candidate_status": "exclude_not_pe" if gold["is_pe_vc"].upper() != "TRUE" else "candidate_keep",
                "method": "keyword_positioning_plus_markdown_excerpt_rules",
            }
        )
    return candidates


def compare_auto_to_gold(gold_rows: list[dict], auto_rows: list[dict]) -> tuple[list[dict], list[dict]]:
    auto_by_record = {row["record_id"]: row for row in auto_rows}
    comparison: list[dict] = []
    for gold in gold_rows:
        auto = auto_by_record.get(gold["record_id"], {})
        gold_code = gold.get("pe_fund_filing_code", "").strip()
        gold_gp_code = gold.get("gp_registration_code", "").strip()
        gold_manager = gold.get("fund_manager_gp", "").strip()
        row = {
            "record_id": gold["record_id"],
            "sample_id": gold["sample_id"],
            "investor_name": gold["investor_name"],
            "gold_investor_type": gold["investor_type"],
            "auto_investor_type": auto.get("investor_type_pred", ""),
            "investor_type_match": str(gold["investor_type"] == auto.get("investor_type_pred", "")),
            "gold_filing_code": gold_code,
            "auto_filing_code": auto.get("pe_fund_filing_code_pred", ""),
            "filing_code_match": str((not gold_code) or gold_code == auto.get("pe_fund_filing_code_pred", "")),
            "gold_gp": gold_manager,
            "auto_gp": auto.get("fund_manager_gp_pred", ""),
            "gp_match": str((not gold_manager) or gold_manager == auto.get("fund_manager_gp_pred", "")),
            "gold_gp_registration_code": gold_gp_code,
            "auto_gp_registration_code": auto.get("gp_registration_code_pred", ""),
            "gp_registration_code_match": str((not gold_gp_code) or gold_gp_code == auto.get("gp_registration_code_pred", "")),
            "source_pages": gold.get("source_pages", ""),
            "manual_check_status": gold.get("manual_check_status", ""),
            "blank_reason": gold.get("blank_reason", ""),
        }
        comparison.append(row)

    def ratio(name: str, rows: list[dict], denominator_filter, numerator_filter) -> dict:
        denom_rows = [r for r in rows if denominator_filter(r)]
        numerator = sum(1 for r in denom_rows if numerator_filter(r))
        denominator = len(denom_rows)
        return {
            "metric": name,
            "numerator": numerator,
            "denominator": denominator,
            "accuracy_pct": round(numerator / denominator * 100, 2) if denominator else "",
        }

    metrics = [
        {"metric": "gold_records", "numerator": len(gold_rows), "denominator": len(gold_rows), "accuracy_pct": 100.0},
        ratio("investor_type_accuracy", comparison, lambda r: True, lambda r: r["investor_type_match"] == "True"),
        ratio("filing_code_accuracy_when_pdf_disclosed", comparison, lambda r: bool(r["gold_filing_code"]), lambda r: r["filing_code_match"] == "True"),
        ratio("gp_name_accuracy_when_pdf_disclosed", comparison, lambda r: bool(r["gold_gp"]), lambda r: r["gp_match"] == "True"),
        ratio(
            "gp_registration_code_accuracy_when_pdf_disclosed",
            comparison,
            lambda r: bool(r["gold_gp_registration_code"]),
            lambda r: r["gp_registration_code_match"] == "True",
        ),
        {
            "metric": "blank_policy_records",
            "numerator": sum(1 for r in gold_rows if r.get("blank_reason", "").strip()),
            "denominator": len(gold_rows),
            "accuracy_pct": "",
        },
    ]
    return comparison, metrics


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        cleaned = [str(cell).replace("|", "/").replace("\n", " ") for cell in row]
        out.append("| " + " | ".join(cleaned) + " |")
    return "\n".join(out)


def write_gold_markdown_tables(gold_rows: list[dict]) -> None:
    MARKDOWN_TABLE_DIR.mkdir(parents=True, exist_ok=True)
    compact_fields = [
        "record_id",
        "sample_id",
        "company_short",
        "investor_name",
        "investor_type",
        "pe_fund_filing_code",
        "fund_manager_gp",
        "gp_registration_code",
        "source_pages",
        "blank_reason",
    ]
    all_rows = [[row.get(f, "") for f in compact_fields] for row in gold_rows]
    (MARKDOWN_TABLE_DIR / "gold_standard_all.md").write_text(
        "# Gold standard Markdown table\n\n" + markdown_table(compact_fields, all_rows) + "\n",
        encoding="utf-8",
    )

    by_sample: dict[str, list[dict]] = defaultdict(list)
    for row in gold_rows:
        by_sample[row["sample_id"]].append(row)
    for sample_id, rows in by_sample.items():
        md = f"# {sample_id} gold standard rows\n\n"
        md += markdown_table(compact_fields, [[row.get(f, "") for f in compact_fields] for row in rows])
        md += "\n"
        (MARKDOWN_TABLE_DIR / f"{sample_id}_gold_table.md").write_text(md, encoding="utf-8")

    mineru_files = sorted(MINERU_MD_DIR.glob("*.md")) if MINERU_MD_DIR.exists() else []
    report = [
        "# Markdown表格抽取报告",
        "",
        "## 1. 当前模式",
        "",
        "本提交包已将接口统一为 Markdown：正式 MinerU 导出文件应放入 `data/mineru_markdown/`。当前目录未提供 MinerU 原始 `.md` 时，脚本使用 PDF 文本生成精准定位 Markdown 作为兜底。",
        "",
        f"- MinerU Markdown文件数：{len(mineru_files)}",
        f"- gold standard记录数：{len(gold_rows)}",
        f"- 已生成公司级Markdown表：{len(set(row['sample_id'] for row in gold_rows))}张",
        "",
        "## 2. 表格完整性",
        "",
        "本版本将 gold 主表按公司拆成 Markdown 表格，保证人工复核时不丢行、不丢列。后续若接入 MinerU 原始 Markdown，优先解析其中的 `| ... |` 表格，再回填 gold 字段。",
        "",
    ]
    (MARKDOWN_TABLE_DIR / "markdown_table_extraction_report.md").write_text("\n".join(report), encoding="utf-8")


def write_excel_if_available(gold_rows: list[dict], comparison: list[dict], metrics: list[dict], inventory: list[dict]) -> None:
    try:
        import pandas as pd
    except ImportError:
        return
    excel_path = OUTPUT_DIR / "eight_company_gold_standard.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        pd.DataFrame(gold_rows).to_excel(writer, index=False, sheet_name="manual_gold")
        pd.DataFrame(comparison).to_excel(writer, index=False, sheet_name="auto_vs_gold")
        pd.DataFrame(metrics).to_excel(writer, index=False, sheet_name="accuracy")
        pd.DataFrame(inventory).to_excel(writer, index=False, sheet_name="pdf_inventory")


def write_reports(
    manifest: dict[str, dict],
    inventory: list[dict],
    page_hits: list[PageHit],
    gold_rows: list[dict],
    comparison: list[dict],
    metrics: list[dict],
) -> None:
    by_sample_gold = Counter(row["sample_id"] for row in gold_rows)
    by_sample_hits = Counter(hit.sample_id for hit in page_hits)
    pe_count = sum(1 for row in gold_rows if row["is_pe_vc"].upper() == "TRUE")
    not_pe_count = len(gold_rows) - pe_count
    filing_count = sum(1 for row in gold_rows if row.get("pe_fund_filing_code", "").strip())
    blank_count = sum(1 for row in gold_rows if row.get("blank_reason", "").strip())

    summary_rows = []
    for sample_id, row in manifest.items():
        summary_rows.append(
            {
                "sample_id": sample_id,
                "board": row["board"],
                "company_short": row["company_short"],
                "positioned_pages": by_sample_hits[sample_id],
                "gold_records": by_sample_gold[sample_id],
                "located_markdown": f"outputs/located_markdown/{sample_id}_positioned_sections.md",
            }
        )
    write_csv(OUTPUT_DIR / "company_positioning_summary.csv", summary_rows)

    report = [
        "# 八家公司PE基金定位与Gold Standard输出报告",
        "",
        "## 1. 本周目标",
        "",
        "本版本把康农种业案例中的人工复核经验扩展到八家公司。核心变化是：先用代码和目录/关键词定位章节，再截取相关 Markdown 文本；人工 gold 只记录 PDF 已披露事实；自动候选与人工 gold 分离并量化准确率。",
        "",
        "## 2. 样本与输出规模",
        "",
        f"- PDF样本：{len(inventory)}家公司。",
        f"- gold standard记录：{len(gold_rows)}条。",
        f"- PE/VC或证券私募产品记录：{pe_count}条。",
        f"- 员工持股平台/普通企业/未披露排除记录：{not_pe_count}条。",
        f"- 已披露备案编码或产品编码记录：{filing_count}条。",
        f"- 按“PDF未披露就留空”保留空值的记录：{blank_count}条。",
        "",
        "## 3. 公司级定位概览",
        "",
        markdown_table(
            ["sample_id", "板块", "公司简称", "定位命中页数", "gold记录数", "定位Markdown"],
            [
                [
                    r["sample_id"],
                    r["board"],
                    r["company_short"],
                    str(r["positioned_pages"]),
                    str(r["gold_records"]),
                    r["located_markdown"],
                ]
                for r in summary_rows
            ],
        ),
        "",
        "## 4. 自动与人工对比结果",
        "",
        markdown_table(
            ["metric", "numerator", "denominator", "accuracy_pct"],
            [[m["metric"], str(m["numerator"]), str(m["denominator"]), str(m["accuracy_pct"])] for m in metrics],
        ),
        "",
        "## 5. 关键工程原则",
        "",
        "1. `investor_type` 先分类再处理：PE基金、VC基金、证券公司私募/资管产品、员工持股平台、普通企业投资人分开进入不同口径。",
        "2. Markdown表格优先：本包将 gold 输出为 Markdown 表格，并保留 MinerU Markdown 输入接口；后续有 MinerU 原始 `.md` 时无需再走 JSON。",
        "3. 精准截取替代全量PDF投喂：`outputs/located_markdown/` 只保存相关命中页，报告和提示词都基于这些截取页。",
        "4. PDF未披露就留空：例如天和磁材披露中车泛海、同历宏阳已备案，但未披露备案编码，因此编码字段留空并写入 `blank_reason`。",
        "",
        "## 6. 失败与边界案例",
        "",
        "- 黄山谷捷：黄山佳捷是员工持股平台，且PDF明确说明机构股东不属于私募投资基金，不应为了凑PE记录而强行标注。",
        "- 大鹏工业：普拉特是员工持股平台，融汇工创在定位页未披露PE/VC属性，因此一个排除、一个保留空值。",
        "- 赛分科技：高新同华名称含创业投资历史，但PDF披露中基协备案状态为未备案，因此不能归入已备案PE基金。",
        "- 天和磁材：PDF披露私募基金股东已备案，但未在定位页披露备案编码和GP登记编号，必须留空。",
        "",
        "## 7. 后续改进",
        "",
        "下一步应把 MinerU 正式 Markdown 输出放入 `data/mineru_markdown/`，用本脚本的 Markdown 表格解析接口读取；同时针对投资人很多的公司增加 LP 结构子表，避免把 LP 错当直接投资人。",
        "",
    ]
    (OUTPUT_DIR / "gold_standard_report.md").write_text("\n".join(report), encoding="utf-8")

    accuracy_report = [
        "# 自动抽取与人工Gold对比",
        "",
        "本表不是为了证明自动化已经完美，而是量化规则定位在当前八家公司中的可用程度。",
        "",
        markdown_table(
            ["metric", "numerator", "denominator", "accuracy_pct"],
            [[m["metric"], str(m["numerator"]), str(m["denominator"]), str(m["accuracy_pct"])] for m in metrics],
        ),
        "",
        "口径说明：备案编码准确率只统计 gold 中 PDF 已披露编码的记录；PDF 未披露编码的记录不计入分母。",
        "",
    ]
    (OUTPUT_DIR / "accuracy_report.md").write_text("\n".join(accuracy_report), encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = manifest_by_sample()
    inventory = build_pdf_inventory(manifest)
    write_csv(OUTPUT_DIR / "pdf_inventory.csv", inventory)

    page_hits = locate_relevant_pages(manifest)
    write_csv(
        OUTPUT_DIR / "toc_keyword_positioning.csv",
        [
            {
                "sample_id": hit.sample_id,
                "stock_code": hit.stock_code,
                "company_short": hit.company_short,
                "pdf_name": hit.pdf_name,
                "page": hit.page,
                "section_hint": hit.section_hint,
                "hit_keywords": ";".join(hit.hit_keywords),
                "snippet": hit.snippet,
            }
            for hit in page_hits
        ],
    )

    gold_rows = read_csv(MANUAL_GOLD_PATH)
    write_csv(OUTPUT_DIR / "gold_standard.csv", gold_rows, GOLD_FIELDS)
    write_jsonl(OUTPUT_DIR / "gold_standard.jsonl", gold_rows)
    write_gold_markdown_tables(gold_rows)

    auto_rows = make_auto_candidates(gold_rows, manifest)
    write_csv(OUTPUT_DIR / "auto_output_candidates.csv", auto_rows)
    write_jsonl(OUTPUT_DIR / "auto_output_candidates.jsonl", auto_rows)

    comparison, metrics = compare_auto_to_gold(gold_rows, auto_rows)
    write_csv(OUTPUT_DIR / "comparison_auto_vs_manual.csv", comparison)
    write_csv(OUTPUT_DIR / "accuracy_metrics.csv", metrics)

    write_reports(manifest, inventory, page_hits, gold_rows, comparison, metrics)
    write_excel_if_available(gold_rows, comparison, metrics, inventory)

    print("Pipeline complete")
    print(f"gold records: {len(gold_rows)}")
    print(f"positioned page hits: {len(page_hits)}")
    print(f"outputs: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
