from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIST_PATH = ROOT / "company_lists" / "week2_2025_company_list.csv"
RAW_PDF_DIR = ROOT / "raw_pdfs" / "week2"
OUTPUT_DIR = ROOT / "outputs" / "week2_sample_outputs"
CANDIDATE_DIR = OUTPUT_DIR / "candidate_texts"
PARSED_DIR = OUTPUT_DIR / "parsed_texts"
JSON_DIR = OUTPUT_DIR / "sample_json"
LOG_DIR = ROOT / "logs"

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

STAR_2025_COMPANIES = [
    ("688411", "海博思创", "北京海博思创科技股份有限公司", "2025-01-27", "2025-01-22", "https://static.cninfo.com.cn/finalpage/2025-01-22/1222389596.PDF", "海博思创首次公开发行股票并在科创板上市招股说明书"),
    ("688545", "兴福电子", "湖北兴福电子材料股份有限公司", "2025-01-22", "2025-01-17", "https://static.cninfo.com.cn/finalpage/2025-01-17/1222355547.PDF", "兴福电子首次公开发行股票并在科创板上市招股说明书"),
    ("688583", "思看科技", "思看科技(杭州)股份有限公司", "2025-01-15", "2025-01-10", "https://static.cninfo.com.cn/finalpage/2025-01-10/1222285798.PDF", "思看科技首次公开发行股票并在科创板上市招股说明书"),
    ("688727", "恒坤新材", "厦门恒坤新材料科技股份有限公司", "2025-11-18", "2025-11-13", "https://static.cninfo.com.cn/finalpage/2025-11-13/1224802223.PDF", "恒坤新材首次公开发行股票并在科创板上市招股说明书"),
    ("688729", "屹唐股份", "北京屹唐半导体科技股份有限公司", "2025-07-08", "2025-07-03", "https://static.cninfo.com.cn/finalpage/2025-07-03/1224068769.PDF", "屹唐股份首次公开发行股票并在科创板上市招股说明书"),
    ("688755", "汉邦科技", "江苏汉邦科技股份有限公司", "2025-05-16", "2025-05-13", "https://static.cninfo.com.cn/finalpage/2025-05-13/1223528584.PDF", "汉邦科技首次公开发行股票并在科创板上市招股说明书"),
    ("688757", "胜科纳米", "胜科纳米(苏州)股份有限公司", "2025-03-25", "2025-03-20", "https://static.cninfo.com.cn/finalpage/2025-03-20/1222846384.PDF", "胜科纳米首次公开发行股票并在科创板上市招股说明书"),
    ("688758", "赛分科技", "苏州赛分科技股份有限公司", "2025-01-10", "2025-01-06", "https://static.cninfo.com.cn/finalpage/2025-01-06/1222238930.PDF", "赛分科技首次公开发行股票并在科创板上市招股说明书"),
    ("688759", "必贝特", "广州必贝特医药股份有限公司", "2025-10-28", "2025-10-23", "https://static.cninfo.com.cn/finalpage/2025-10-23/1224726268.PDF", "必贝特首次公开发行股票并在科创板上市招股说明书"),
    ("688765", "禾元生物", "武汉禾元生物科技股份有限公司", "2025-10-28", "2025-10-20", "https://static.cninfo.com.cn/finalpage/2025-10-20/1224719933.PDF", "禾元生物首次公开发行股票并在科创板上市招股说明书"),
    ("688775", "影石创新", "影石创新科技股份有限公司", "2025-06-11", "2025-06-06", "https://static.cninfo.com.cn/finalpage/2025-06-06/1223788474.PDF", "影石创新首次公开发行股票并在科创板上市招股说明书"),
    ("688783", "西安奕材", "西安奕斯伟材料科技股份有限公司", "2025-10-28", "2025-10-22", "https://static.cninfo.com.cn/finalpage/2025-10-22/1224723727.PDF", "西安奕材首次公开发行股票并在科创板上市招股说明书"),
    ("688790", "昂瑞微", "北京昂瑞微电子技术股份有限公司", "2025-12-16", "2025-12-11", "https://static.cninfo.com.cn/finalpage/2025-12-11/1224867086.PDF", "昂瑞微首次公开发行股票并在科创板上市招股说明书"),
    ("688795", "摩尔线程", "摩尔线程智能科技(北京)股份有限公司", "2025-12-05", "2025-11-28", "https://static.cninfo.com.cn/finalpage/2025-11-28/1224831699.PDF", "摩尔线程首次公开发行股票并在科创板上市招股说明书"),
    ("688796", "百奥赛图", "百奥赛图(北京)医药科技股份有限公司", "2025-12-10", "2025-12-04", "https://static.cninfo.com.cn/finalpage/2025-12-04/1224848797.PDF", "百奥赛图首次公开发行股票并在科创板上市招股说明书"),
    ("688802", "沐曦股份", "沐曦集成电路(上海)股份有限公司", "2025-12-17", "2025-12-11", "https://static.cninfo.com.cn/finalpage/2025-12-11/1224867078.PDF", "沐曦股份首次公开发行股票并在科创板上市招股说明书"),
    ("688805", "健信超导", "宁波健信超导科技股份有限公司", "2025-12-24", "2025-12-19", "https://static.cninfo.com.cn/finalpage/2025-12-19/1224886206.PDF", "健信超导首次公开发行股票并在科创板上市招股说明书"),
    ("688807", "优迅股份", "厦门优迅芯片股份有限公司", "2025-12-19", "2025-12-12", "https://static.cninfo.com.cn/finalpage/2025-12-12/1224870082.PDF", "优迅股份首次公开发行股票并在科创板上市招股说明书"),
    ("688809", "强一股份", "强一半导体(苏州)股份有限公司", "2025-12-30", "2025-12-25", "https://static.cninfo.com.cn/finalpage/2025-12-25/1224897120.PDF", "强一股份首次公开发行股票并在科创板上市招股说明书"),
]


def ensure_dirs() -> None:
    for path in [RAW_PDF_DIR, OUTPUT_DIR, CANDIDATE_DIR, PARSED_DIR, JSON_DIR, LOG_DIR, LIST_PATH.parent]:
        path.mkdir(parents=True, exist_ok=True)


def read_rows() -> list[dict[str, str]]:
    with LIST_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_rows(rows: list[dict[str, str]]) -> None:
    LIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LIST_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COMPANY_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def pdf_path_for(row: dict[str, str]) -> Path:
    return RAW_PDF_DIR / f"{row['sample_id']}_{row['stock_code']}.pdf"


def compact(text: str, limit: int = 1400) -> str:
    return re.sub(r"\s+", " ", text).strip()[:limit]


def source_page_url(code: str) -> str:
    return f"https://www.cninfo.com.cn/new/disclosure/stock?stockCode={code}"

