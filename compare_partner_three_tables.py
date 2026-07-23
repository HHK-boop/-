"""Compare Chen Yuang's three-table workbooks with HHK's Week 6 workbooks."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


COMPANIES = [
    ("603418", "友升股份", "603418_友升股份_三表抽取示范.xlsx", "603418_友升股份_三表抽取.xlsx"),
    ("001282", "三联锻造", "001282_三联锻造_三表抽取(2).xlsx", "001282_三联锻造_三表抽取.xlsx"),
    ("301581", "黄山谷捷", "301581_黄山谷捷_三表抽取(2).xlsx", "301581_黄山谷捷_三表抽取.xlsx"),
    ("301563", "云汉芯城", "301563_云汉芯城_三表抽取(2).xlsx", "301563_云汉芯城_三表抽取.xlsx"),
    ("688758", "赛分科技", "688758_赛分科技_三表抽取(2).xlsx", "688758_赛分科技_三表抽取.xlsx"),
    ("688775", "影石创新", "688775_影石创新_三表抽取(2).xlsx", "688775_影石创新_三表抽取.xlsx"),
    ("920100", "三协电机", "920100_三协电机_三表抽取(2).xlsx", "920100_三协电机_三表抽取.xlsx"),
    ("920116", "星图测控", "920116_星图测控_三表抽取(2).xlsx", "920116_星图测控_三表抽取.xlsx"),
]

SHEETS = ["1_认缴流量", "2_股权结构存量", "3_schema_cross_check"]
EXPECTED_HEADERS = {
    "1_认缴流量": ["PDF页码", "增资日期", "认购方", "认购数量(万股)", "认购金额(万元)", "认购价格(元/股)", "原文证据"],
    "2_股权结构存量": ["PDF页码", "时点", "股权结构口径", "股东名称", "持股数(万股)", "出资额(万元注册资本)", "持股比例", "原文证据"],
    "3_schema_cross_check": ["检查类型", "事件日期", "PDF页码", "检查项", "核对区间", "校验结果", "备注信息/复核提示"],
}


def clean_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    text = text.replace(".0", "") if re.fullmatch(r"\d+\.0", text) else text
    return text


def norm_num(value: Any) -> str:
    text = clean_text(value).replace(",", "").replace("%", "")
    if text == "":
        return ""
    try:
        num = float(text)
    except ValueError:
        return clean_text(value)
    if abs(num) < 1e-12:
        return "0"
    return f"{num:.6f}".rstrip("0").rstrip(".")


def read_sheet(path: Path, sheet: str) -> pd.DataFrame:
    try:
        raw = pd.read_excel(path, sheet_name=sheet, dtype=object, engine="openpyxl", header=None)
    except ValueError:
        return pd.DataFrame()
    raw = raw.dropna(how="all").reset_index(drop=True)
    expected = EXPECTED_HEADERS.get(sheet, [])
    header_idx = 0
    best_score = -1
    for idx, row in raw.iterrows():
        cells = [clean_text(v) for v in row.tolist()]
        score = sum(1 for h in expected if h in cells)
        if score > best_score:
            best_score = score
            header_idx = idx
    if best_score >= 3:
        headers = [clean_text(v) or f"Unnamed_{i}" for i, v in enumerate(raw.iloc[header_idx].tolist())]
        df = raw.iloc[header_idx + 1 :].copy()
        df.columns = headers
    else:
        df = pd.read_excel(path, sheet_name=sheet, dtype=object, engine="openpyxl")
    df = df.dropna(how="all")
    df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")]
    df.columns = [clean_text(c) for c in df.columns]
    for col in df.columns:
        df[col] = df[col].map(clean_text)
    if len(df.columns):
        df = df[df.apply(lambda row: any(clean_text(v) for v in row), axis=1)]
    return df.reset_index(drop=True)


def key_for_row(sheet: str, row: pd.Series) -> str:
    if sheet == "1_认缴流量":
        return "|".join(
            [
                clean_text(row.get("PDF页码", "")),
                clean_text(row.get("增资日期", "")),
                clean_text(row.get("认购方", "")),
                norm_num(row.get("认购数量(万股)", "")),
                norm_num(row.get("认购金额(万元)", "")),
                norm_num(row.get("认购价格(元/股)", "")),
            ]
        )
    if sheet == "2_股权结构存量":
        return "|".join(
            [
                clean_text(row.get("PDF页码", "")),
                clean_text(row.get("时点", "")),
                clean_text(row.get("股权结构口径", "")),
                clean_text(row.get("股东名称", "")),
                norm_num(row.get("持股数(万股)", "")),
                norm_num(row.get("出资额(万元注册资本)", "")),
                norm_num(row.get("持股比例", "")),
            ]
        )
    return "|".join(clean_text(row.get(c, "")) for c in row.index[:6])


def count_nonempty_by_col(df: pd.DataFrame, cols: list[str]) -> dict[str, int]:
    return {col: int(df[col].astype(str).str.strip().ne("").sum()) if col in df.columns else 0 for col in cols}


def summarize_sheet(stock_code: str, company: str, sheet: str, partner: pd.DataFrame, mine: pd.DataFrame) -> dict[str, Any]:
    partner_keys = set(partner.apply(lambda r: key_for_row(sheet, r), axis=1)) if not partner.empty else set()
    mine_keys = set(mine.apply(lambda r: key_for_row(sheet, r), axis=1)) if not mine.empty else set()
    partner_keys.discard("")
    mine_keys.discard("")
    same = len(partner_keys & mine_keys)
    partner_only = len(partner_keys - mine_keys)
    mine_only = len(mine_keys - partner_keys)
    status = "基本一致"
    if partner_only or mine_only:
        status = "存在差异"
    if not len(partner) and not len(mine):
        status = "双方均无记录"
    elif abs(len(partner) - len(mine)) >= 10:
        status = "差异较大"
    return {
        "stock_code": stock_code,
        "company_short": company,
        "sheet": sheet,
        "partner_rows": len(partner),
        "my_rows": len(mine),
        "row_diff_my_minus_partner": len(mine) - len(partner),
        "matched_key_count": same,
        "partner_only_key_count": partner_only,
        "my_only_key_count": mine_only,
        "status": status,
        "partner_columns": "；".join(partner.columns.astype(str).tolist()),
        "my_columns": "；".join(mine.columns.astype(str).tolist()),
    }


def sample_only_rows(sheet: str, df: pd.DataFrame, only_keys: set[str], owner: str, limit: int = 8) -> list[dict[str, str]]:
    rows = []
    for _, row in df.iterrows():
        key = key_for_row(sheet, row)
        if key not in only_keys:
            continue
        item = {"owner": owner, "sheet": sheet, "key": key}
        if sheet == "1_认缴流量":
            for col in ["PDF页码", "增资日期", "认购方", "认购数量(万股)", "认购金额(万元)", "认购价格(元/股)", "原文证据"]:
                item[col] = clean_text(row.get(col, ""))
        elif sheet == "2_股权结构存量":
            for col in ["PDF页码", "时点", "股权结构口径", "股东名称", "持股数(万股)", "出资额(万元注册资本)", "持股比例", "原文证据"]:
                item[col] = clean_text(row.get(col, ""))
        else:
            for col in list(row.index[:8]):
                item[col] = clean_text(row.get(col, ""))
        rows.append(item)
        if len(rows) >= limit:
            break
    return rows


def infer_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare partner and HHK three-table workbooks.")
    parser.add_argument("--root", default=str(infer_root()), help="HHK Week 6 root.")
    parser.add_argument(
        "--partner-dir",
        default=r"C:\Users\29818\Documents\xwechat_files\wxid_mdm501526cx122_1a20\msg\file\2026-07",
        help="Directory containing Chen Yuang's workbooks.",
    )
    parser.add_argument("--my-dir", default="final/三表抽取_仿样式", help="Directory containing HHK workbooks.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    partner_dir = Path(args.partner_dir)
    my_dir = (root / args.my_dir).resolve()
    out_dir = root / "review" / "陈雨昂_vs_霍泓锟_互查"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    detail_rows = []
    missing_files = []

    for code, company, partner_name, my_name in COMPANIES:
        partner_path = partner_dir / partner_name
        my_path = my_dir / my_name
        if not partner_path.exists() or not my_path.exists():
            missing_files.append({"stock_code": code, "company_short": company, "partner_exists": partner_path.exists(), "my_exists": my_path.exists()})
            continue
        for sheet in SHEETS:
            partner_df = read_sheet(partner_path, sheet)
            my_df = read_sheet(my_path, sheet)
            summary_rows.append(summarize_sheet(code, company, sheet, partner_df, my_df))
            partner_keys = set(partner_df.apply(lambda r: key_for_row(sheet, r), axis=1)) if not partner_df.empty else set()
            my_keys = set(my_df.apply(lambda r: key_for_row(sheet, r), axis=1)) if not my_df.empty else set()
            partner_keys.discard("")
            my_keys.discard("")
            detail_rows.extend(sample_only_rows(sheet, partner_df, partner_keys - my_keys, "陈雨昂"))
            detail_rows.extend(sample_only_rows(sheet, my_df, my_keys - partner_keys, "霍泓锟"))

    summary = pd.DataFrame(summary_rows)
    detail = pd.DataFrame(detail_rows)
    missing = pd.DataFrame(missing_files)

    summary.to_csv(out_dir / "互查_逐公司逐表数量对比.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(out_dir / "互查_差异样例.csv", index=False, encoding="utf-8-sig")
    missing.to_csv(out_dir / "互查_缺失文件.csv", index=False, encoding="utf-8-sig")

    (out_dir / "互查_机器可读摘要.json").write_text(
        json.dumps(
            {
                "summary_rows": summary_rows,
                "missing_files": missing_files,
                "partner_dir": str(partner_dir),
                "my_dir": str(my_dir),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"summary_rows={len(summary_rows)}")
    print(f"detail_rows={len(detail_rows)}")
    print(f"out_dir={out_dir}")


if __name__ == "__main__":
    main()
