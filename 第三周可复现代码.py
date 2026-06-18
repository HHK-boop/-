from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
SOURCE_XLSX = ROOT / "source_company_list_star_2021_2025.xlsx"
LIST_PATH = ROOT / "company_lists" / "week3_extended_company_list.csv"
RAW_PDF_DIR = ROOT / "raw_pdfs" / "week3"
OUTPUT_DIR = ROOT / "outputs" / "week3_sample_outputs"
PARSED_DIR = OUTPUT_DIR / "parsed_texts"
CANDIDATE_DIR = OUTPUT_DIR / "candidate_texts"
JSON_DIR = OUTPUT_DIR / "sample_json"
LOG_DIR = ROOT / "logs"
SOURCE_NOTES_DIR = ROOT / "source_notes"
REVIEW_DIR = ROOT / "review"
REPORT_DIR = ROOT / "weekly_reports"

COMPANY_FIELDS = [
    "sample_id",
    "company_name",
    "stock_code",
    "exchange",
    "board",
    "listing_date",
    "ipo_year",
    "source_platform",
    "source_page_url",
    "prospectus_title",
    "prospectus_url",
    "prospectus_version",
    "prospectus_date",
    "download_status",
    "parse_status",
    "locate_status",
    "extract_status",
    "review_status",
    "notes",
]

KEYWORDS = [
    "历次增资",
    "股权转让",
    "股本形成",
    "股本演变",
    "历史沿革",
    "发行前股东",
    "股东情况",
    "外部投资者",
    "投资协议",
    "特殊投资条款",
    "私募基金",
    "创业投资",
    "增资",
    "认购",
    "股份锁定",
]

EVENT_KEYWORDS = ["增资", "股权转让", "认购", "出资", "投资协议", "外部投资", "私募基金", "创业投资"]
GOOD_NAME_TERMS = ["投资", "基金", "创投", "资本", "合伙", "私募", "产业", "深创投", "华金", "中证", "金石", "基石", "毅达", "红杉", "高瓴"]
BAD_NAME_TERMS = [
    "招股说明书",
    "发行人",
    "本次发行",
    "注册资本",
    "实收资本",
    "资本公积",
    "报告期",
    "序号",
    "合计",
    "股东名称",
    "出资额",
    "出资比例",
    "持股比例",
    "认购金额",
    "认购方式",
    "万元",
    "万股",
    "现金",
    "是否属于",
    "战略投资者",
    "投资方",
    "投资者",
    "特殊投资",
    "特殊权利",
    "基金管理人",
    "产品管理人",
    "执行事务合伙人",
    "实际控制人",
]


def ensure_dirs() -> None:
    for path in [LIST_PATH.parent, RAW_PDF_DIR, OUTPUT_DIR, PARSED_DIR, CANDIDATE_DIR, JSON_DIR, LOG_DIR, SOURCE_NOTES_DIR, REVIEW_DIR, REPORT_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_rows() -> list[dict[str, str]]:
    with LIST_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_rows(rows: list[dict[str, Any]]) -> None:
    write_csv(LIST_PATH, rows, COMPANY_FIELDS)


def source_page_url(code: str) -> str:
    return f"https://www.cninfo.com.cn/new/disclosure/stock?stockCode={code}"


def pdf_path_for(row: dict[str, str]) -> Path:
    return RAW_PDF_DIR / f"{row['sample_id']}_{row['stock_code']}.pdf"


def compact(text: str, limit: int = 1800) -> str:
    return re.sub(r"\s+", " ", text).strip()[:limit]


def local_source_path(value: str) -> Path:
    raw = Path(str(value))
    return raw if raw.is_absolute() else WORKSPACE / raw


def copy_or_download_pdf(row: dict[str, str], source_local_file: str = "") -> tuple[str, int, str]:
    dest = pdf_path_for(row)
    message = ""
    try:
        src = local_source_path(source_local_file) if source_local_file else None
        if src is not None and src.is_file():
            shutil.copy2(src, dest)
            return "success", dest.stat().st_size, f"copied_from_local_source={src}"
        if dest.exists():
            return "success", dest.stat().st_size, "reused_existing_week3_pdf"
        if "bse.cn/disclosure/" in row["prospectus_url"].lower():
            shell_dest = str(dest.relative_to(ROOT)) if dest.is_relative_to(ROOT) else str(dest)
            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "& { param($uri, $out) $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri $uri -OutFile $out -UseBasicParsing -TimeoutSec 120 }",
                    row["prospectus_url"],
                    shell_dest,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return "success", dest.stat().st_size, "downloaded_from_bse_with_powershell"
        request = urllib.request.Request(
            row["prospectus_url"],
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": row.get("source_page_url") or "https://www.bse.cn/",
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            dest.write_bytes(response.read())
        return "success", dest.stat().st_size, "downloaded_from_prospectus_url"
    except Exception as exc:  # noqa: BLE001
        message = str(exc)
    return "fail", 0, message


def page_blocks(text: str) -> list[tuple[str, int, int, str]]:
    matches = list(re.finditer(r"<!-- page:(\d+) -->", text))
    blocks = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        blocks.append((match.group(1), match.start(), end, text[start:end]))
    return blocks


def score_page(page_text: str) -> tuple[int, str]:
    matched = [kw for kw in KEYWORDS if kw in page_text]
    score = 0
    for kw in matched:
        if kw in {"历次增资", "股权转让", "股本形成", "股本演变", "历史沿革"}:
            score += 5
        elif kw in {"发行前股东", "股东情况", "外部投资者", "投资协议", "特殊投资条款"}:
            score += 3
        else:
            score += 1
    return score, "、".join(matched[:6])


def clean_name(name: str) -> str:
    name = re.sub(r"\s+", "", name)
    name = re.sub(r"^[0-9一二三四五六七八九十、.．]+", "", name)
    return name.strip("，。；：:、[]【】<>《》- ")


def is_good_name(name: str) -> bool:
    if len(name) < 2 or len(name) > 42:
        return False
    if name in {"有限合伙", "投资", "基金", "资本", "创投"}:
        return False
    if any(bad in name for bad in BAD_NAME_TERMS):
        return False
    return any(term in name for term in GOOD_NAME_TERMS)


def investor_type(name: str) -> tuple[str, str]:
    if any(k in name for k in ["员工", "持股平台", "咨询", "管理中心"]):
        return "员工持股平台/持股平台", "uncertain"
    if any(k in name for k in ["政府", "国有", "产业", "引导"]):
        return "政府基金/产业资本", "uncertain"
    if any(k in name for k in ["创业投资", "创投", "私募", "股权投资", "投资基金", "基金", "资本", "深创投", "红杉", "高瓴"]):
        return "VC/PE", "yes"
    if "有限公司" in name or "有限合伙" in name:
        return "机构投资者", "uncertain"
    return "无法判断", "uncertain"


def find_investor_names(text: str) -> list[str]:
    names: list[str] = []
    normalized = re.sub(r"\s+", "", text)
    patterns = [
        r"[\u4e00-\u9fa5A-Za-z0-9（）()·]{2,38}?(?:创业投资企业（有限合伙）|创业投资企业|创业投资中心|股权投资基金|投资基金|产业基金|投资中心|投资合伙企业|投资管理合伙企业|投资管理有限公司|投资有限公司|资本管理有限公司|私募基金管理有限公司|有限合伙)",
        r"[\u4e00-\u9fa5A-Za-z0-9（）()·]{2,20}(?:投资|基金|创投|资本|基石|毅达|红杉|高瓴|深创投|华金|中证|金石)",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, normalized):
            name = clean_name(match)
            if is_good_name(name) and name not in names:
                names.append(name)
    return names[:20]


def find_event_date(text: str) -> str:
    match = re.search(r"(20\d{2}|19\d{2})\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日", text)
    if match:
        return re.sub(r"\s+", "", match.group(0))
    match = re.search(r"(20\d{2}|19\d{2})[-./]\d{1,2}[-./]\d{1,2}", text)
    return match.group(0) if match else ""


def extract_amount(text: str) -> float | None:
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:万|万元)", text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def validate_json(data: dict[str, Any]) -> tuple[str, str, str, str]:
    missing: list[str] = []
    type_errors: list[str] = []
    logic_errors: list[str] = []
    company = data.get("company")
    events = data.get("financing_events")
    if not isinstance(company, dict):
        missing.append("company")
        company = {}
    if not isinstance(events, list):
        missing.append("financing_events")
        events = []
    for field in ["company_name", "stock_code", "board", "prospectus_title", "prospectus_url"]:
        if not company.get(field):
            missing.append(f"company.{field}")
    for idx, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            type_errors.append(f"event[{idx}]")
            continue
        for field in ["event_order", "event_type", "source_page", "evidence_text"]:
            if event.get(field) in (None, ""):
                missing.append(f"event[{idx}].{field}")
        if not isinstance(event.get("investors", []), list):
            type_errors.append(f"event[{idx}].investors")
    status = "pass" if not (missing or type_errors or logic_errors) else "revise"
    return status, "；".join(missing), "；".join(type_errors), "；".join(logic_errors)


def dump_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
