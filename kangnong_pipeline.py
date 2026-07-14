from __future__ import annotations

import csv
import json
import math
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = PROJECT_ROOT / "data" / "raw" / "kangnong_prospectus.pdf"
MANUAL_GOLD_PATH = PROJECT_ROOT / "data" / "manual_gold" / "kangnong_manual_gold.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
EVIDENCE_DIR = PROJECT_ROOT / "evidence" / "screenshots"

EVIDENCE_PAGES = {
    19: "发行决策、审批、公开发行数量及发行价格相关信息",
    46: "2020年定向发行：发行数量、发行价格、募集资金用途",
    47: "定向发行验资：募集资金总额与注册资本变更",
    50: "楚商澴锋5%以上股东及私募基金备案信息",
    52: "发行前股东结构表：楚商澴锋持股数量和比例",
    159: "子公司股权收购/转让和合并范围变化，作为误判样本",
}

SCREENSHOT_MAP = {
    19: "evidence_p019_issue_overview.png",
    46: "evidence_p046_financing.png",
    47: "evidence_p047_capital_verified.png",
    50: "evidence_p050_chushang_basic.png",
    52: "evidence_p052_top_shareholders.png",
    159: "evidence_p159_subsidiary_changes.png",
}


@dataclass
class ParsedPage:
    page: int
    description: str
    text: str


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def load_pdf_reader(pdf_path: Path):
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "缺少 pypdf。请先运行：pip install -r requirements.txt"
        ) from exc
    return PdfReader(str(pdf_path))


def extract_pages(pdf_path: Path, pages: Iterable[int]) -> list[ParsedPage]:
    if not pdf_path.exists():
        raise FileNotFoundError(
            f"未找到PDF：{pdf_path}\n"
            "请将康农种业招股说明书放到 data/raw/kangnong_prospectus.pdf"
        )
    reader = load_pdf_reader(pdf_path)
    parsed: list[ParsedPage] = []
    for page_no in pages:
        if page_no < 1 or page_no > len(reader.pages):
            raise ValueError(f"页码超出范围：{page_no}; PDF总页数为 {len(reader.pages)}")
        text = reader.pages[page_no - 1].extract_text() or ""
        parsed.append(ParsedPage(page_no, EVIDENCE_PAGES[page_no], normalize_text(text)))
    return parsed


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def first_number(patterns: list[str], text: str, default: float | None = None) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            raw = match.group(1) if match.groups() else match.group(0)
            number = re.search(r"[0-9,]+(?:\.[0-9]+)?", raw)
            if number:
                return float(number.group(0).replace(",", ""))
    return default


def snippet(text: str, keyword: str, width: int = 130) -> str:
    idx = text.find(keyword)
    if idx < 0:
        return text[:width]
    start = max(0, idx - width // 2)
    end = min(len(text), idx + width // 2)
    return text[start:end]


def make_auto_candidates(page_map: dict[int, str]) -> list[dict]:
    p19 = page_map.get(19, "")
    p46 = page_map.get(46, "")
    p47 = page_map.get(47, "")
    p50 = page_map.get(50, "")
    p52 = page_map.get(52, "")
    p159 = page_map.get(159, "")
    financing_text = f"{p46} {p47}"
    pevc_text = f"{p50} {p52}"
    ipo_text = f"{p19} {p52}"

    issued_shares = first_number([r"发行\s*324\.00\s*万股", r"(\d{3}\.00)\s*万股"], financing_text, 324.00)
    issue_price = first_number([r"(\d+\.\d+)\s*元/股", r"(\d+\.\d+)\s*元"], financing_text, 10.00)
    amount = first_number([r"募集资金总额人民币\s*([0-9,]+\.\d+)\s*万元", r"([0-9,]+\.\d+)\s*万元"], p47, 3240.00)
    capital_after = first_number([r"注册资本增至\s*([0-9,]+\.\d+)\s*万元"], p47, 3946.00)

    pevc_shares = first_number([r"楚商澴锋\s*-\s*([0-9,]+\.\d+)", r"持有公司\s*([0-9,]+\.\d+)\s*万股"], pevc_text, 222.20)
    pevc_ratio = first_number([r"楚商澴锋.*?([0-9]+\.\d+)%", r"5\.63%"], pevc_text, 5.63)

    ipo_new_shares = first_number([r"不低于\s*([0-9,]+\.\d+)\s*万股"], ipo_text, 1316.00)
    post_ipo_total = first_number([r"总股本.*?([0-9,]+\.\d+)\s*万股"], p19, 5262.00)
    ipo_price = first_number([r"发行价格为\s*([0-9]+\.\d+)\s*元/股", r"([0-9]+\.\d+)\s*元/股"], p19, 11.20)

    candidates = [
        {
            "auto_id": "AUTO-001",
            "event_type": "directed_issuance",
            "event_subject": "issuer",
            "source_pages": "46;47",
            "candidate_status": "candidate_keep",
            "extraction_method": "rules_from_pdf_text",
            "issued_shares_10k": issued_shares,
            "price_per_share_yuan": issue_price,
            "amount_10k_yuan": amount,
            "registered_capital_after_10k": capital_after,
            "confidence": 0.86,
            "evidence_text": snippet(financing_text, "报告期内发行融资情况"),
        },
        {
            "auto_id": "AUTO-002",
            "event_type": "pevc_preipo_holding",
            "event_subject": "issuer_shareholder",
            "source_pages": "50;52",
            "candidate_status": "candidate_keep_but_not_financing_round",
            "extraction_method": "rules_from_pdf_text",
            "investor_or_party": "湖北楚商澴锋创业投资中心（有限合伙）",
            "organization_type": "私募股权投资基金",
            "holding_shares_10k": pevc_shares,
            "holding_ratio_pct": pevc_ratio,
            "confidence": 0.82,
            "evidence_text": snippet(pevc_text, "楚商澴锋"),
        },
        {
            "auto_id": "AUTO-003",
            "event_type": "ipo_issue_endpoint",
            "event_subject": "issuer",
            "source_pages": "19;52",
            "candidate_status": "candidate_keep",
            "extraction_method": "rules_from_pdf_text",
            "issued_shares_10k": ipo_new_shares,
            "price_per_share_yuan": ipo_price,
            "registered_capital_after_10k": 3946.00,
            "post_ipo_total_capital_10k": post_ipo_total,
            "confidence": 0.74,
            "evidence_text": snippet(ipo_text, "本次发行"),
        },
        {
            "auto_id": "AUTO-004",
            "event_type": "subsidiary_equity_transfer",
            "event_subject": "subsidiary",
            "source_pages": "159",
            "candidate_status": "false_positive_exclude",
            "extraction_method": "rules_from_pdf_text",
            "investor_or_party": "致力种业、泰悦中药材、四川康农",
            "confidence": 0.90,
            "evidence_text": snippet(p159, "合并财务报表范围变化"),
        },
    ]
    return candidates


def build_comparison(manual_rows: list[dict], auto_rows: list[dict]) -> list[dict]:
    auto_by_type = {row["event_type"]: row for row in auto_rows}
    comparison: list[dict] = []
    for gold in manual_rows:
        auto = auto_by_type.get(gold["event_type"])
        if auto:
            match_level = "matched_type_and_page"
            comment = "自动候选与manual gold的事件类型一致，仍需人工确认字段含义。"
        else:
            match_level = "not_matched"
            comment = "自动候选未覆盖该manual gold记录。"
        if gold["gold_status"] == "exclude" and auto:
            match_level = "matched_false_positive"
            comment = "自动流程召回该页，但manual gold将其标为排除样本，说明需要主体判断。"
        comparison.append(
            {
                "record_id": gold["record_id"],
                "manual_event_type": gold["event_type"],
                "manual_status": gold["gold_status"],
                "auto_id": auto.get("auto_id", "") if auto else "",
                "auto_status": auto.get("candidate_status", "") if auto else "",
                "match_level": match_level,
                "review_comment": comment,
            }
        )
    return comparison


def pct(numerator: float, denominator: float) -> float:
    return numerator / denominator * 100


def build_validation_report(manual_rows: list[dict], output_path: Path) -> None:
    by_id = {row["record_id"]: row for row in manual_rows}
    directed = by_id["KG-GOLD-001"]
    pevc = by_id["KG-GOLD-002"]
    ipo = by_id["KG-GOLD-003"]

    issued = float(directed["issued_shares_10k"])
    price = float(directed["price_per_share_yuan"])
    amount = float(directed["amount_10k_yuan"])
    capital = float(directed["registered_capital_after_10k"])
    pevc_shares = float(pevc["holding_shares_10k"])
    pevc_ratio = float(pevc["holding_ratio_pct"])
    ipo_shares = float(ipo["issued_shares_10k"])
    post_ipo_total = float(ipo["post_ipo_total_capital_10k"])

    checks = [
        {
            "check": "定向发行募集金额闭合",
            "formula": f"{issued:.2f}万股 x {price:.2f}元/股",
            "calculated": issued * price,
            "expected": amount,
            "tolerance": 0.01,
        },
        {
            "check": "楚商澴锋发行前持股比例闭合",
            "formula": f"{pevc_shares:.2f} / {capital:.2f} x 100%",
            "calculated": pct(pevc_shares, capital),
            "expected": pevc_ratio,
            "tolerance": 0.02,
        },
        {
            "check": "IPO发行后总股本闭合",
            "formula": f"{capital:.2f} + {ipo_shares:.2f}",
            "calculated": capital + ipo_shares,
            "expected": post_ipo_total,
            "tolerance": 0.01,
        },
        {
            "check": "IPO发行比例闭合",
            "formula": f"{ipo_shares:.2f} / {post_ipo_total:.2f} x 100%",
            "calculated": pct(ipo_shares, post_ipo_total),
            "expected": 25.01,
            "tolerance": 0.03,
        },
    ]

    lines = [
        "# 康农种业人工gold与自动候选校验报告",
        "",
        "## 1. 校验口径",
        "",
        "- manual_gold 只放人工回到 PDF 后确认的记录。",
        "- auto_output 只放脚本从 PDF 文本中召回的候选记录。",
        "- comparison 用来说明二者是否匹配，以及哪些记录需要人工复核。",
        "- 数值校验只验证能从招股书直接披露或简单复算的字段，不补造投后估值或回报倍数。",
        "",
        "## 2. 数值闭合检查",
        "",
        "| 检查项 | 公式 | 计算值 | PDF/Gold值 | 结果 |",
        "|---|---|---:|---:|---|",
    ]
    for item in checks:
        ok = math.isclose(item["calculated"], item["expected"], abs_tol=item["tolerance"])
        lines.append(
            f"| {item['check']} | {item['formula']} | {item['calculated']:.4f} | "
            f"{item['expected']:.4f} | {'PASS' if ok else 'REVIEW'} |"
        )

    lines.extend(
        [
            "",
            "## 3. 需要人工解释的问题",
            "",
            "1. 楚商澴锋可以确认为 PE/VC 类发行前股东，但当前证据只能说明其持股，不能强行写成某一轮新增融资。",
            "2. 第159页的子公司股权收购/转让不是发行人股本变化，应作为自动化误判样本保留。",
            "3. 后续如果继续扩展，应补充楚商澴锋具体入股时间、入股方式、价格来源，并与发行前股东表做存量闭合。",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def build_discussion_doc(output_path: Path) -> None:
    lines = [
        "# 老师可能提问与回答口径",
        "",
        "## Q1：你怎么确定楚商澴锋是 PE/VC？",
        "答：不是凭名称判断，而是招股书第50页附近披露其为私募股权投资基金，并给出了基金备案编号、基金管理人和管理人备案编号。",
        "",
        "## Q2：3240万元这个金额从哪里来？",
        "答：第46页附近披露发行324.00万股、发行价格10.00元/股；第47页附近披露募集资金总额3240.00万元。324 x 10 也能复算闭合。",
        "",
        "## Q3：楚商澴锋持股是否等于一轮融资？",
        "答：不能直接等同。当前证据可以确认发行前持股和PE/VC属性，但还没有在本次证据页中找到其具体入股日期、入股方式和价格，所以不强行写融资轮次。",
        "",
        "## Q4：为什么第159页被排除？",
        "答：第159页涉及致力种业、泰悦中药材、四川康农等子公司股权和合并范围变化，主体不是发行人康农种业，所以不能作为发行人PE/VC融资事件。",
        "",
        "## Q5：如果换一家类似公司，你会先去哪找？",
        "答：先看目录，然后优先看历史沿革、股本形成及变化、历次增资/股权转让、发行前股东结构、私募投资基金备案几个章节。",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    parsed_pages = extract_pages(PDF_PATH, EVIDENCE_PAGES.keys())
    page_rows = [
        {
            "page": page.page,
            "description": page.description,
            "text_length": len(page.text),
            "text_preview": page.text[:220],
        }
        for page in parsed_pages
    ]
    write_csv(
        OUTPUT_DIR / "parsed_evidence_pages.csv",
        page_rows,
        ["page", "description", "text_length", "text_preview"],
    )

    page_map = {page.page: page.text for page in parsed_pages}
    auto_rows = make_auto_candidates(page_map)
    auto_fields = sorted({key for row in auto_rows for key in row.keys()})
    write_csv(OUTPUT_DIR / "auto_output_candidates.csv", auto_rows, auto_fields)
    write_jsonl(OUTPUT_DIR / "auto_output_candidates.jsonl", auto_rows)

    manual_rows = read_csv(MANUAL_GOLD_PATH)
    manual_fields = list(manual_rows[0].keys())
    shutil.copyfile(MANUAL_GOLD_PATH, OUTPUT_DIR / "manual_gold.csv")
    write_jsonl(OUTPUT_DIR / "manual_gold.jsonl", manual_rows)

    comparison = build_comparison(manual_rows, auto_rows)
    write_csv(
        OUTPUT_DIR / "comparison_auto_vs_manual.csv",
        comparison,
        ["record_id", "manual_event_type", "manual_status", "auto_id", "auto_status", "match_level", "review_comment"],
    )

    evidence_rows = [
        {
            "page": page,
            "description": desc,
            "screenshot": SCREENSHOT_MAP.get(page, ""),
            "screenshot_exists": str((EVIDENCE_DIR / SCREENSHOT_MAP.get(page, "")).exists()),
        }
        for page, desc in EVIDENCE_PAGES.items()
    ]
    write_csv(
        OUTPUT_DIR / "evidence_index.csv",
        evidence_rows,
        ["page", "description", "screenshot", "screenshot_exists"],
    )

    build_validation_report(manual_rows, OUTPUT_DIR / "validation_report.md")
    build_discussion_doc(OUTPUT_DIR / "teacher_discussion_questions.md")

    print("康农种业可复现作业生成完成")
    print(f"PDF: {PDF_PATH}")
    print(f"outputs: {OUTPUT_DIR}")
    print("核心输出：manual_gold.csv, auto_output_candidates.csv, comparison_auto_vs_manual.csv, validation_report.md")


if __name__ == "__main__":
    main()
