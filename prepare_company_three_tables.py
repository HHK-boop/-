"""Prepare per-company three-table workbook data in the teacher reference style."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


SUB_HEADERS = ["PDF页码", "增资日期", "认购方", "认购数量(万股)", "认购金额(万元)", "认购价格(元/股)", "原文证据"]
SNAP_HEADERS = [
    "PDF页码",
    "时点",
    "股权结构口径",
    "总股本(万股)",
    "总出资额(万元注册资本)",
    "股东名称",
    "持股数(万股)",
    "出资额(万元注册资本)",
    "持股比例",
    "原文证据",
]
CHECK_HEADERS = [
    "检查类型",
    "事件日期",
    "PDF页码",
    "检查项",
    "核对区间",
    "上一时点股本/持股数(万股)",
    "上一时点出资额(万元注册资本)",
    "本次认购/变化(万股)",
    "预期本期股本/持股数(万股)",
    "PDF披露本期股本/持股数(万股)",
    "差额(万股)",
    "校验结果",
    "备注信息/复核提示",
]


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def compact_text(value: Any, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def number_or_blank(value: Any, *, zero_blank: bool = True, min_value: float | None = None, max_value: float | None = None) -> float | str:
    if value is None or str(value).strip() == "":
        return ""
    try:
        num = float(str(value).replace(",", "").replace("%", ""))
    except ValueError:
        return str(value)
    if zero_blank and abs(num) < 1e-12:
        return ""
    if min_value is not None and num < min_value:
        return ""
    if max_value is not None and num > max_value:
        return ""
    return round(num, 6)


def best_price(row: pd.Series) -> float | str:
    direct = number_or_blank(row.get("subscription_price_yuan", ""), min_value=0.1, max_value=500)
    if direct != "":
        return direct
    return number_or_blank(row.get("computed_price_yuan", ""), min_value=0.1, max_value=500)


def status_text(status: str) -> str:
    mapping = {"PASS": "pass", "INFO": "待复核", "REVIEW": "待复核", "FAIL": "fail"}
    return mapping.get(status, status or "待复核")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare JSON for reference-style three-table workbooks.")
    parser.add_argument("--root", default=".", help="Repository root.")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    manifest = read_csv(root / "data" / "manifest" / "company_manifest.csv")
    sub = read_csv(root / "final" / "subscription_final.csv")
    snap = read_csv(root / "final" / "equity_snapshot_final.csv")
    transfer = read_csv(root / "final" / "transfer_final.csv")
    cross = read_csv(root / "validation" / "cross_check.csv")

    sub_lookup = sub.set_index("record_id").to_dict("index") if "record_id" in sub.columns else {}
    snap_lookup = snap.set_index("record_id").to_dict("index") if "record_id" in snap.columns else {}

    companies = []
    for _, c in manifest.iterrows():
        code = c["stock_code"]
        company_sub = sub[sub["stock_code"] == code].copy()
        company_snap = snap[snap["stock_code"] == code].copy()
        company_transfer = transfer[transfer["stock_code"] == code].copy()
        company_cross = cross[cross["stock_code"] == code].copy()

        company_sub = company_sub.sort_values(["event_date", "pdf_page", "record_id"], kind="stable")
        company_snap = company_snap.sort_values(["time_point", "pdf_page", "record_id"], kind="stable")

        sub_rows = []
        for _, r in company_sub.iterrows():
            sub_rows.append(
                {
                    "PDF页码": r.get("pdf_page", ""),
                    "增资日期": r.get("event_date", ""),
                    "认购方": r.get("subscriber_name", ""),
                    "认购数量(万股)": number_or_blank(r.get("subscription_shares_wan", "")),
                    "认购金额(万元)": number_or_blank(r.get("subscription_amount_wan", "")),
                    "认购价格(元/股)": best_price(r),
                    "原文证据": compact_text(r.get("source_evidence", "")),
                }
            )

        snap_rows = []
        for _, r in company_snap.iterrows():
            snap_rows.append(
                {
                    "PDF页码": r.get("pdf_page", ""),
                    "时点": r.get("time_point", ""),
                    "股权结构口径": r.get("equity_structure_scope", ""),
                    "总股本(万股)": number_or_blank(r.get("total_shares_wan", "")),
                    "总出资额(万元注册资本)": number_or_blank(r.get("total_capital_wan", "")),
                    "股东名称": r.get("shareholder_name", ""),
                    "持股数(万股)": number_or_blank(r.get("shares_held_wan", "")),
                    "出资额(万元注册资本)": number_or_blank(r.get("capital_contribution_wan", "")),
                    "持股比例": number_or_blank(r.get("shareholding_ratio_pct", ""), zero_blank=False),
                    "原文证据": compact_text(r.get("source_evidence", ""), limit=120),
                }
            )

        missing_price = sum(1 for row in sub_rows if row["认购价格(元/股)"] == "")
        missing_ratio = sum(1 for row in snap_rows if row["持股比例"] == "")
        check_rows = [
            {
                "检查类型": "schema",
                "事件日期": "",
                "PDF页码": "",
                "检查项": "认缴流量",
                "核对区间": "",
                "上一时点股本/持股数(万股)": "",
                "上一时点出资额(万元注册资本)": "",
                "本次认购/变化(万股)": "",
                "预期本期股本/持股数(万股)": "",
                "PDF披露本期股本/持股数(万股)": "",
                "差额(万股)": "",
                "校验结果": "pass" if len(sub_rows) else "待复核",
                "备注信息/复核提示": f"sheet名称、字段匹配、{len(sub_rows)}条记录、{missing_price}条未披露或异常价格留空、字段完整性和类型可校验",
            },
            {
                "检查类型": "schema",
                "事件日期": "",
                "PDF页码": "",
                "检查项": "股权结构存量",
                "核对区间": "",
                "上一时点股本/持股数(万股)": "",
                "上一时点出资额(万元注册资本)": "",
                "本次认购/变化(万股)": "",
                "预期本期股本/持股数(万股)": "",
                "PDF披露本期股本/持股数(万股)": "",
                "差额(万股)": "",
                "校验结果": "pass" if len(snap_rows) else "待复核",
                "备注信息/复核提示": f"sheet名称、字段匹配、{len(snap_rows)}条记录、{missing_ratio}条无持股比例、t0/关键时点需人工核对",
            },
            {
                "检查类型": "schema",
                "事件日期": "",
                "PDF页码": "",
                "检查项": "股权转让Final",
                "核对区间": "",
                "上一时点股本/持股数(万股)": "",
                "上一时点出资额(万元注册资本)": "",
                "本次认购/变化(万股)": "",
                "预期本期股本/持股数(万股)": "",
                "PDF披露本期股本/持股数(万股)": "",
                "差额(万股)": "",
                "校验结果": "pass" if len(company_transfer) else "待复核",
                "备注信息/复核提示": f"Final确认转让{len(company_transfer)}条；未确认候选保留在review目录，不在本模板中另设转让sheet",
            },
        ]

        for _, r in company_cross.iterrows():
            source = sub_lookup.get(r.get("record_id", ""), snap_lookup.get(r.get("record_id", ""), {}))
            check_item = "认购价格一致性" if r.get("check_type") == "subscription_price" else "持股比例合计"
            check_rows.append(
                {
                    "检查类型": r.get("check_type", ""),
                    "事件日期": source.get("event_date", source.get("time_point", "")),
                    "PDF页码": source.get("pdf_page", ""),
                    "检查项": check_item,
                    "核对区间": source.get("batch_label", source.get("time_point", "")),
                    "上一时点股本/持股数(万股)": "",
                    "上一时点出资额(万元注册资本)": "",
                    "本次认购/变化(万股)": source.get("subscription_shares_wan", ""),
                    "预期本期股本/持股数(万股)": "",
                    "PDF披露本期股本/持股数(万股)": source.get("total_shares_wan", ""),
                    "差额(万股)": number_or_blank(r.get("metric", ""), zero_blank=False),
                    "校验结果": status_text(r.get("status", "")),
                    "备注信息/复核提示": compact_text(r.get("detail", ""), limit=180),
                }
            )

        companies.append(
            {
                "stock_code": code,
                "company_short": c["company_short"],
                "output_name": f"{code}_{c['company_short']}_三表抽取.xlsx",
                "sheets": {
                    "1_认缴流量": {"headers": SUB_HEADERS, "rows": sub_rows},
                    "2_股权结构存量": {"headers": SNAP_HEADERS, "rows": snap_rows},
                    "3_schema_cross_check": {"headers": CHECK_HEADERS, "rows": check_rows},
                },
            }
        )

    out_dir = root / "tmp_workbook"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "company_three_table_data.json"
    out_path.write_text(json.dumps({"companies": companies}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Prepared {len(companies)} company workbook payloads: {out_path}")


if __name__ == "__main__":
    main()
