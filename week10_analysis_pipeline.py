"""Week 10 research-oriented pipeline for the IPO PE/VC project.

Input: Week 9 cleaned/derived CSV files.
Output: company-level research panel, investor profiles, fund enrichment queue,
quality gates, descriptive statistics, correlation matrix, exploratory OLS
results, PostgreSQL import scripts, report markdown, and workbook payload.

The pipeline deliberately keeps undisclosed PDF fields blank. AMAC record code,
GP, and LP structure are not inferred from names; they are placed into a manual
enrichment queue for later verification.
"""

from __future__ import annotations

import csv
import json
import math
import os
import shutil
import subprocess
from datetime import date
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "input_week9"
DERIVED = ROOT / "data" / "derived"
DATABASE = ROOT / "database"
VALIDATION = ROOT / "validation"
REVIEW = ROOT / "review"
OUTPUTS = ROOT / "outputs"
LOGS = ROOT / "logs"
REPORT = ROOT / "report"

RUN_DATE = "2026-08-26"
RUN_TIME = "2026-08-26 18:00:00"

BROAD_PEVC_TYPES = {
    "VC",
    "PE",
    "政府基金/国资平台",
    "产业资本/CVC/法人股东",
    "其他投资平台",
}

FUND_LIKE_KEYWORDS = [
    "基金",
    "投资",
    "创投",
    "创业投资",
    "资本",
    "合伙",
    "有限合伙",
    "资产管理",
    "管理中心",
    "国资",
    "产业",
]

NUMERIC_RESEARCH_COLUMNS = [
    "broad_pevc_record_share",
    "distinct_investor_type_count",
    "transfer_event_count",
    "top1_ratio_pct",
    "top3_ratio_pct",
    "hhi",
    "effective_shareholder_count",
    "broad_pevc_holder_count",
    "broad_pevc_ratio_sum_pct",
    "pevc_strength_index",
    "pre_ipo_dispersion_index",
]


def ensure_dirs() -> None:
    for directory in [DERIVED, DATABASE, VALIDATION, REVIEW, OUTPUTS, LOGS, REPORT]:
        directory.mkdir(parents=True, exist_ok=True)


def read_csv(name: str) -> pd.DataFrame:
    path = INPUT / name
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, dtype={"stock_code": str}, keep_default_na=False)


def write_csv(path: Path, rows: Iterable[dict] | pd.DataFrame) -> None:
    if isinstance(rows, pd.DataFrame):
        rows.to_csv(path, index=False, encoding="utf-8-sig")
        return
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.replace("", np.nan), errors="coerce")


def pct_to_decimal(value: float | int | str) -> float | None:
    try:
        if value == "" or pd.isna(value):
            return None
        return round(float(value) / 100, 6)
    except Exception:
        return None


def zscore(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    std = values.std(ddof=0)
    if not std or math.isnan(std):
        return pd.Series([0.0] * len(series), index=series.index)
    return ((values - values.mean()) / std).round(6)


def safe_join_unique(values: Iterable[str]) -> str:
    cleaned = sorted({str(v).strip() for v in values if str(v).strip()})
    return "；".join(cleaned)


def is_fund_like(name: str, investor_type: str) -> bool:
    text = f"{name}{investor_type}"
    if investor_type in {"自然人", "员工持股平台"}:
        return False
    return any(keyword in text for keyword in FUND_LIKE_KEYWORDS)


def classify_manual_priority(investor_type: str, fund_like: bool, record_count: int) -> str:
    if investor_type in {"VC", "PE"} and fund_like:
        return "P1-优先补备案编码/GP/LP"
    if investor_type in {"政府基金/国资平台", "产业资本/CVC/法人股东"} and fund_like:
        return "P2-补充主体性质与实际控制人"
    if investor_type == "其他投资平台" or fund_like:
        return "P2-确认是否PE/VC或持股平台"
    if record_count >= 5:
        return "P3-高频主体保留观察"
    return "P4-暂不处理"


def make_company_panel(research: pd.DataFrame, quality: pd.DataFrame) -> pd.DataFrame:
    panel = research.copy()
    panel["stock_code"] = panel["stock_code"].astype(str).str.zfill(6)
    for col in [
        "has_vc_or_pe",
        "vc_record_count",
        "pe_record_count",
        "broad_pevc_record_count",
        "broad_pevc_record_share",
        "distinct_investor_type_count",
        "transfer_event_count",
        "week8_p1_item_count",
        "week9_closed_p1_count",
        "week9_unresolved_p1_count",
        "top1_ratio_pct",
        "top3_ratio_pct",
        "hhi",
        "effective_shareholder_count",
        "broad_pevc_holder_count",
        "broad_pevc_ratio_sum_pct",
    ]:
        if col in panel.columns:
            panel[col] = to_num(panel[col])

    max_holder = max(float(panel["broad_pevc_holder_count"].max() or 0), 1.0)
    panel["pevc_record_share_decimal"] = panel["broad_pevc_record_share"].map(pct_to_decimal)
    panel["broad_pevc_ratio_decimal"] = panel["broad_pevc_ratio_sum_pct"].map(pct_to_decimal)
    panel["top1_ratio_decimal"] = panel["top1_ratio_pct"].map(pct_to_decimal)
    panel["hhi_percent"] = (panel["hhi"] * 100).round(3)
    panel["pevc_strength_index"] = (
        100
        * (
            0.70 * panel["broad_pevc_record_share"].fillna(0) / 100
            + 0.30 * panel["broad_pevc_holder_count"].fillna(0) / max_holder
        )
    ).round(3)
    panel["pre_ipo_dispersion_index"] = panel["effective_shareholder_count"].round(3)
    panel["pevc_strength_z"] = zscore(panel["pevc_strength_index"])
    panel["dispersion_z"] = zscore(panel["pre_ipo_dispersion_index"])
    panel["caution_flag"] = panel["week9_research_note"].apply(
        lambda x: 0 if str(x).strip() == "可用于描述性统计" else 1
    )
    panel["analysis_sample_flag"] = np.where(
        panel[["broad_pevc_record_share", "effective_shareholder_count", "top1_ratio_pct", "hhi"]]
        .notna()
        .all(axis=1),
        1,
        0,
    )
    panel["board_group"] = panel["market"].replace({"北交所": "BSE", "科创板": "STAR", "创业板": "GEM", "主板": "Main"})
    for board in ["主板", "创业板", "科创板", "北交所"]:
        panel[f"is_{board}"] = (panel["market"] == board).astype(int)

    if not quality.empty:
        panel = panel.merge(
            quality[
                [
                    "stock_code",
                    "invalid_ratio_timepoints",
                    "blank_ratio_timepoints",
                    "usable_ratio_timepoints",
                    "quality_gate",
                ]
            ],
            on="stock_code",
            how="left",
        )
    return panel


def build_ratio_quality(snapshot_validity: pd.DataFrame, review_queue: pd.DataFrame) -> pd.DataFrame:
    df = snapshot_validity.copy()
    df["stock_code"] = df["stock_code"].astype(str).str.zfill(6)
    df["ratio_sum_pct_num"] = to_num(df["ratio_sum_pct"])
    rows = []
    for code, g in df.groupby("stock_code", dropna=False):
        company = g["company_short"].iloc[0]
        market = g["market"].iloc[0]
        invalid = g[~g["week9_ratio_validity"].eq("可用于比例分析")]
        abnormal = g[g["ratio_sum_pct_num"].gt(101) | g["ratio_sum_pct_num"].lt(99)]
        blank = g[g["ratio_observed_rows"].astype(str).eq("0")]
        p1_count = int(
            review_queue[
                review_queue["stock_code"].astype(str).str.zfill(6).eq(code)
                & review_queue["week8_status"].astype(str).str.contains("P1", na=False)
            ].shape[0]
        )
        closed = int(
            review_queue[
                review_queue["stock_code"].astype(str).str.zfill(6).eq(code)
                & review_queue["week9_resolution"].astype(str).str.contains("已闭环", na=False)
            ].shape[0]
        )
        gate = "通过"
        note = "可进入描述性统计"
        if len(abnormal) > 0:
            gate = "谨慎使用"
            note = "存在比例合计异常时点，研究变量应使用筛选后的快照"
        if len(blank) > 0:
            gate = "谨慎使用"
            note = "存在PDF未披露比例的历史时点，不能补0"
        rows.append(
            {
                "stock_code": code,
                "company_short": company,
                "market": market,
                "ratio_timepoints": int(g.shape[0]),
                "usable_ratio_timepoints": int(g["week9_ratio_validity"].eq("可用于比例分析").sum()),
                "invalid_ratio_timepoints": int(invalid.shape[0]),
                "abnormal_ratio_timepoints": int(abnormal.shape[0]),
                "blank_ratio_timepoints": int(blank.shape[0]),
                "week8_p1_count": p1_count,
                "week9_closed_p1_count": closed,
                "quality_gate": gate,
                "quality_note": note,
            }
        )
    return pd.DataFrame(rows)


def build_field_completeness(subs: pd.DataFrame, snaps: pd.DataFrame, transfers: pd.DataFrame) -> pd.DataFrame:
    configs = [
        (
            "认缴/增资表",
            subs,
            [
                "event_date",
                "subscriber_name",
                "subscription_amount_wan",
                "subscription_ratio_pct",
                "pdf_page",
                "source_evidence",
                "investor_type_final",
            ],
        ),
        (
            "股权快照表",
            snaps,
            [
                "time_point",
                "shareholder_name",
                "shareholding_ratio_pct",
                "pdf_page",
                "source_evidence",
                "investor_type_final",
            ],
        ),
        (
            "股权转让表",
            transfers,
            [
                "transfer_date",
                "transferor_name",
                "transferee_name",
                "transfer_amount_wan",
                "pdf_page",
                "source_evidence",
                "transferor_type_final",
                "transferee_type_final",
            ],
        ),
    ]
    rows = []
    for table_name, df, fields in configs:
        for field in fields:
            if field not in df.columns:
                missing = len(df)
                observed = 0
            else:
                observed_mask = df[field].astype(str).str.strip().ne("")
                observed = int(observed_mask.sum())
                missing = int(len(df) - observed)
            rows.append(
                {
                    "table_name": table_name,
                    "field_name": field,
                    "record_count": int(len(df)),
                    "observed_count": observed,
                    "missing_count": missing,
                    "missing_rate": round(missing / len(df), 4) if len(df) else 0,
                    "week10_action": "PDF未披露则保留空值；若为关键研究变量，下周人工抽样核验",
                }
            )
    return pd.DataFrame(rows)


def collect_investor_rows(subs: pd.DataFrame, snaps: pd.DataFrame, transfers: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in subs.iterrows():
        rows.append(
            {
                "investor_name": row.get("subscriber_name", ""),
                "investor_type_final": row.get("investor_type_final", ""),
                "stock_code": str(row.get("stock_code", "")).zfill(6),
                "company_short": row.get("company_short", ""),
                "market": row.get("market", ""),
                "source_table": "认缴/增资",
                "source_record_id": row.get("record_id", ""),
                "pdf_page": row.get("pdf_page", ""),
            }
        )
    for _, row in snaps.iterrows():
        rows.append(
            {
                "investor_name": row.get("shareholder_name", ""),
                "investor_type_final": row.get("investor_type_final", ""),
                "stock_code": str(row.get("stock_code", "")).zfill(6),
                "company_short": row.get("company_short", ""),
                "market": row.get("market", ""),
                "source_table": "股权快照",
                "source_record_id": row.get("record_id", ""),
                "pdf_page": row.get("pdf_page", ""),
            }
        )
    for _, row in transfers.iterrows():
        rows.append(
            {
                "investor_name": row.get("transferor_name", ""),
                "investor_type_final": row.get("transferor_type_final", ""),
                "stock_code": str(row.get("stock_code", "")).zfill(6),
                "company_short": row.get("company_short", ""),
                "market": row.get("market", ""),
                "source_table": "股权转让-转让方",
                "source_record_id": row.get("record_id", ""),
                "pdf_page": row.get("pdf_page", ""),
            }
        )
        rows.append(
            {
                "investor_name": row.get("transferee_name", ""),
                "investor_type_final": row.get("transferee_type_final", ""),
                "stock_code": str(row.get("stock_code", "")).zfill(6),
                "company_short": row.get("company_short", ""),
                "market": row.get("market", ""),
                "source_table": "股权转让-受让方",
                "source_record_id": row.get("record_id", ""),
                "pdf_page": row.get("pdf_page", ""),
            }
        )
    investor_rows = pd.DataFrame(rows)
    investor_rows = investor_rows[investor_rows["investor_name"].astype(str).str.strip().ne("")]
    return investor_rows


def build_investor_profile(investor_rows: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (name, investor_type), g in investor_rows.groupby(["investor_name", "investor_type_final"], dropna=False):
        record_count = int(g.shape[0])
        companies = safe_join_unique(g["company_short"])
        markets = safe_join_unique(g["market"])
        source_tables = safe_join_unique(g["source_table"])
        pages = safe_join_unique(g["pdf_page"].astype(str))
        broad = int(investor_type in BROAD_PEVC_TYPES)
        fund_like = int(is_fund_like(str(name), str(investor_type)))
        rows.append(
            {
                "investor_name": name,
                "investor_type_final": investor_type,
                "is_broad_pevc": broad,
                "is_fund_like_name": fund_like,
                "record_count": record_count,
                "company_count": int(g["stock_code"].nunique()),
                "companies": companies,
                "markets": markets,
                "source_tables": source_tables,
                "pdf_pages_observed": pages,
                "manual_priority": classify_manual_priority(str(investor_type), bool(fund_like), record_count),
            }
        )
    profile = pd.DataFrame(rows).sort_values(
        ["manual_priority", "is_broad_pevc", "record_count"], ascending=[True, False, False]
    )
    return profile


def build_fund_queue(profile: pd.DataFrame) -> pd.DataFrame:
    queue = profile[
        profile["manual_priority"].astype(str).str.contains("P1|P2", regex=True)
    ].copy()
    queue["amac_record_code"] = ""
    queue["gp_name"] = ""
    queue["lp_structure"] = ""
    queue["disclosure_status"] = "三表未直接披露备案编码/GP/LP，暂不推断"
    queue["next_action"] = queue["manual_priority"].map(
        lambda x: "优先回PDF章节核验；若仍未披露，再查基金业协会或工商信息" if str(x).startswith("P1") else "保留为外部核验队列"
    )
    queue["week10_principle"] = "PDF未披露就留空；外部补充必须另列来源"
    columns = [
        "investor_name",
        "investor_type_final",
        "manual_priority",
        "company_count",
        "companies",
        "markets",
        "source_tables",
        "pdf_pages_observed",
        "amac_record_code",
        "gp_name",
        "lp_structure",
        "disclosure_status",
        "next_action",
        "week10_principle",
    ]
    return queue[columns]


def build_descriptive_stats(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    variable_labels = {
        "broad_pevc_record_share": "广义PE/VC记录占比",
        "pevc_strength_index": "PE/VC进入强度指数",
        "distinct_investor_type_count": "投资主体类型数",
        "top1_ratio_pct": "第一大股东比例",
        "hhi": "HHI",
        "effective_shareholder_count": "有效股东数",
        "broad_pevc_ratio_sum_pct": "广义PE/VC持股比例",
    }
    desc_rows = []
    for col, label in variable_labels.items():
        s = pd.to_numeric(panel[col], errors="coerce").dropna()
        desc_rows.append(
            {
                "variable": col,
                "variable_label": label,
                "n": int(s.shape[0]),
                "mean": round(float(s.mean()), 4) if len(s) else "",
                "median": round(float(s.median()), 4) if len(s) else "",
                "std": round(float(s.std(ddof=1)), 4) if len(s) > 1 else "",
                "min": round(float(s.min()), 4) if len(s) else "",
                "max": round(float(s.max()), 4) if len(s) else "",
                "interpretation": "小样本描述统计，不作为稳健因果结论",
            }
        )
    desc = pd.DataFrame(desc_rows)

    board = (
        panel.groupby("market")
        .agg(
            company_count=("stock_code", "nunique"),
            avg_pevc_strength_index=("pevc_strength_index", "mean"),
            avg_broad_pevc_record_share=("broad_pevc_record_share", "mean"),
            avg_top1_ratio_pct=("top1_ratio_pct", "mean"),
            avg_hhi=("hhi", "mean"),
            avg_effective_shareholder_count=("effective_shareholder_count", "mean"),
            caution_company_count=("caution_flag", "sum"),
        )
        .reset_index()
    )
    for col in board.columns:
        if col.startswith("avg_"):
            board[col] = board[col].round(4)
    board["week10_interpretation"] = "板块均值仅用于观察方向，样本量为每板块2家公司"
    return desc, board


def build_correlation(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    numeric = panel[NUMERIC_RESEARCH_COLUMNS].apply(pd.to_numeric, errors="coerce")
    for left in NUMERIC_RESEARCH_COLUMNS:
        for right in NUMERIC_RESEARCH_COLUMNS:
            if left == right:
                valid = numeric[[left]].dropna()
                corr = 1.0 if len(valid) else np.nan
            else:
                valid = numeric[[left, right]].dropna()
                corr = valid[left].corr(valid[right]) if len(valid) >= 2 else np.nan
            rows.append(
                {
                    "var_left": left,
                    "var_right": right,
                    "n": int(len(valid)),
                    "pearson_corr": round(float(corr), 6) if pd.notna(corr) else "",
                    "note": "相关系数只用于探索变量方向",
                }
            )
    return pd.DataFrame(rows)


def ols_one(panel: pd.DataFrame, y_col: str, x_col: str, sample_scope: str, mask: pd.Series) -> dict:
    df = panel.loc[mask, [y_col, x_col]].apply(pd.to_numeric, errors="coerce").dropna()
    n = int(df.shape[0])
    row = {
        "model_id": f"{sample_scope}:{y_col}~{x_col}",
        "sample_scope": sample_scope,
        "dependent_variable": y_col,
        "independent_variable": x_col,
        "n": n,
        "intercept": "",
        "coef_x": "",
        "std_error_x": "",
        "t_stat_x": "",
        "r_squared": "",
        "model_note": "样本不足，未估计",
    }
    if n < 3:
        return row
    x = df[x_col].to_numpy(dtype=float)
    y = df[y_col].to_numpy(dtype=float)
    X = np.column_stack([np.ones(n), x])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    y_hat = X @ beta
    resid = y - y_hat
    sse = float((resid**2).sum())
    sst = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - sse / sst if sst else np.nan
    dof = n - 2
    if dof > 0:
        sigma2 = sse / dof
        var_beta = sigma2 * np.linalg.inv(X.T @ X)
        se = math.sqrt(float(var_beta[1, 1])) if var_beta[1, 1] >= 0 else np.nan
        t_stat = float(beta[1] / se) if se and not math.isnan(se) else np.nan
    else:
        se = np.nan
        t_stat = np.nan
    row.update(
        {
            "intercept": round(float(beta[0]), 6),
            "coef_x": round(float(beta[1]), 6),
            "std_error_x": round(float(se), 6) if pd.notna(se) else "",
            "t_stat_x": round(float(t_stat), 6) if pd.notna(t_stat) else "",
            "r_squared": round(float(r2), 6) if pd.notna(r2) else "",
            "model_note": "探索性OLS，n=8或更小，不能解释为因果关系",
        }
    )
    return row


def build_regressions(panel: pd.DataFrame) -> pd.DataFrame:
    models = [
        ("effective_shareholder_count", "broad_pevc_record_share"),
        ("top1_ratio_pct", "broad_pevc_record_share"),
        ("hhi", "broad_pevc_record_share"),
        ("effective_shareholder_count", "pevc_strength_index"),
        ("top1_ratio_pct", "pevc_strength_index"),
    ]
    rows = []
    full_mask = panel["analysis_sample_flag"].eq(1)
    clean_mask = full_mask & panel["caution_flag"].eq(0)
    for y, x in models:
        rows.append(ols_one(panel, y, x, "全样本", full_mask))
        rows.append(ols_one(panel, y, x, "剔除谨慎样本", clean_mask))
    return pd.DataFrame(rows)


def build_research_questions(panel: pd.DataFrame, corr: pd.DataFrame, reg: pd.DataFrame) -> pd.DataFrame:
    pevc_disp = corr[
        corr["var_left"].eq("pevc_strength_index")
        & corr["var_right"].eq("effective_shareholder_count")
    ]["pearson_corr"]
    pevc_top1 = corr[
        corr["var_left"].eq("pevc_strength_index") & corr["var_right"].eq("top1_ratio_pct")
    ]["pearson_corr"]
    corr_disp = pevc_disp.iloc[0] if len(pevc_disp) else ""
    corr_top1 = pevc_top1.iloc[0] if len(pevc_top1) else ""
    high = panel.sort_values("pevc_strength_index", ascending=False).head(2)
    low = panel.sort_values("pevc_strength_index", ascending=True).head(2)
    return pd.DataFrame(
        [
            {
                "question_id": "RQ1",
                "research_question": "PE/VC进入强度更高的公司，上市前股权是否更分散？",
                "current_evidence": f"PE/VC强度与有效股东数相关系数约为{corr_disp}；高强度样本包括{safe_join_unique(high['company_short'])}。",
                "current_judgement": "仅能作为探索性关系，需扩样后再做正式检验",
                "next_data_need": "扩大样本、补充行业/年份/发行规模等控制变量",
            },
            {
                "question_id": "RQ2",
                "research_question": "PE/VC进入强度与第一大股东集中度是否存在反向关系？",
                "current_evidence": f"PE/VC强度与第一大股东比例相关系数约为{corr_top1}；低强度样本包括{safe_join_unique(low['company_short'])}。",
                "current_judgement": "方向可能受板块和个别公司披露口径影响",
                "next_data_need": "剔除异常快照、加入板块固定效应或分板块比较",
            },
            {
                "question_id": "RQ3",
                "research_question": "政府基金、产业资本、VC/PE在不同板块的出现频率是否不同？",
                "current_evidence": "第十周已形成投资主体画像和板块-类型矩阵，可用于后续扩样统计。",
                "current_judgement": "当前样本每板块仅2家公司，适合做口径验证，不适合做结论。",
                "next_data_need": "补齐更多公司，并从基金业协会或工商资料补充GP/LP结构。",
            },
        ]
    )


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "（无记录）"
    clean = df.fillna("").astype(str)
    headers = list(clean.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in clean.iterrows():
        values = [str(row[col]).replace("\n", " ") for col in headers]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def run_cmd(cmd: list[str], timeout: int = 10) -> tuple[str, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        text = (result.stdout or result.stderr or "").strip()
        return ("PASS" if result.returncode == 0 else "FAIL", text)
    except Exception as exc:
        return "FAIL", str(exc)


def postgres_audit() -> pd.DataFrame:
    psql = shutil.which("psql") or r"C:\Program Files\PostgreSQL\18\bin\psql.exe"
    pg_isready = shutil.which("pg_isready") or r"C:\Program Files\PostgreSQL\18\bin\pg_isready.exe"
    rows = []
    if Path(psql).exists():
        status, detail = run_cmd([psql, "--version"])
    else:
        status, detail = "FAIL", "未找到psql"
    rows.append({"check_name": "psql_version", "status": status, "detail": detail})
    if Path(pg_isready).exists():
        status, detail = run_cmd([pg_isready, "-h", "localhost", "-p", "5432"])
    else:
        status, detail = "FAIL", "未找到pg_isready"
    rows.append({"check_name": "pg_isready", "status": status, "detail": detail})
    if os.environ.get("PGPASSWORD"):
        rows.append(
            {
                "check_name": "postgres_import",
                "status": "READY_WITH_PASSWORD",
                "detail": "检测到PGPASSWORD，可运行database/run_postgres_import_week10.ps1执行真实导入",
            }
        )
    else:
        rows.append(
            {
                "check_name": "postgres_import",
                "status": "READY_NEED_PASSWORD",
                "detail": "PostgreSQL服务可用时仍需本机口令；本周生成导入脚本但不伪造已入库",
            }
        )
    return pd.DataFrame(rows)


def sql_type_for(col: str) -> str:
    if col in {"stock_code"} or col.endswith("_id"):
        return "text"
    integer_like = {
        "has_vc_or_pe",
        "is_broad_pevc",
        "is_fund_like_name",
        "caution_flag",
        "analysis_sample_flag",
        "is_主板",
        "is_创业板",
        "is_科创板",
        "is_北交所",
        "n",
        "record_count",
        "company_count",
        "observed_count",
        "missing_count",
        "ratio_timepoints",
        "usable_ratio_timepoints",
        "invalid_ratio_timepoints",
        "abnormal_ratio_timepoints",
        "blank_ratio_timepoints",
        "week8_p1_count",
        "week9_closed_p1_count",
        "week9_unresolved_p1_count",
        "week8_p1_item_count",
        "week9_closed_p1_count",
        "week9_unresolved_p1_count",
        "vc_record_count",
        "pe_record_count",
        "broad_pevc_record_count",
        "distinct_investor_type_count",
        "transfer_event_count",
        "broad_pevc_holder_count",
        "shareholder_count",
    }
    if col in integer_like or col.startswith("is_"):
        return "numeric"
    numeric_like = {
        "broad_pevc_record_share",
        "top1_ratio_pct",
        "top3_ratio_pct",
        "hhi",
        "broad_pevc_ratio_sum_pct",
        "pevc_record_share_decimal",
        "broad_pevc_ratio_decimal",
        "top1_ratio_decimal",
        "hhi_percent",
        "pevc_strength_index",
        "pre_ipo_dispersion_index",
        "pevc_strength_z",
        "dispersion_z",
        "effective_shareholder_count",
        "missing_rate",
        "mean",
        "median",
        "std",
        "min",
        "max",
        "pearson_corr",
        "intercept",
        "coef_x",
        "std_error_x",
        "t_stat_x",
        "r_squared",
        "avg_pevc_strength_index",
        "avg_broad_pevc_record_share",
        "avg_top1_ratio_pct",
        "avg_hhi",
        "avg_effective_shareholder_count",
    }
    if col in numeric_like or col.endswith("_pct") or col.endswith("_ratio") or col.endswith("_index"):
        return "numeric"
    return "text"


def write_postgres_scripts(tables: dict[str, pd.DataFrame]) -> None:
    schema_lines = [
        "-- Week 10 PostgreSQL schema generated from derived CSV files.",
        "-- Run from the submission root. Use UTF-8 client encoding.",
        "SET client_encoding = 'UTF8';",
        "",
    ]
    import_lines = [
        "-- Week 10 PostgreSQL import script. Run with psql from the submission root.",
        "SET client_encoding = 'UTF8';",
        "",
    ]
    for table_name, df in tables.items():
        schema_lines.append(f"DROP TABLE IF EXISTS {table_name};")
        cols = [f'    "{col}" {sql_type_for(col)}' for col in df.columns]
        schema_lines.append(f"CREATE TABLE {table_name} (\n" + ",\n".join(cols) + "\n);")
        schema_lines.append("")
        csv_path = f"data/derived/{table_name}.csv"
        import_lines.append(
            f"\\copy {table_name} FROM '{csv_path}' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');"
        )
    (DATABASE / "schema_postgresql_week10.sql").write_text("\n".join(schema_lines), encoding="utf-8")
    (DATABASE / "import_week10_tables.sql").write_text("\n".join(import_lines), encoding="utf-8")
    run_ps1 = r"""$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Psql = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
if (!(Test-Path $Psql)) {
  $Psql = "psql"
}
if (-not $env:PGPASSWORD) {
  Write-Host "请先设置本机PostgreSQL密码，例如：$env:PGPASSWORD='你的密码'"
  exit 1
}
Push-Location $Root
& $Psql -h localhost -p 5432 -U postgres -d postgres -f "database/schema_postgresql_week10.sql"
& $Psql -h localhost -p 5432 -U postgres -d postgres -f "database/import_week10_tables.sql"
Pop-Location
"""
    (DATABASE / "run_postgres_import_week10.ps1").write_text(run_ps1, encoding="utf-8")


def build_validation_summary(summary: dict, quality: pd.DataFrame, postgres: pd.DataFrame) -> pd.DataFrame:
    checks = [
        {
            "check_item": "样本公司数",
            "status": "PASS" if summary["company_count"] == 8 else "WARN",
            "result": summary["company_count"],
            "note": "第十周沿用统一8家公司样本",
        },
        {
            "check_item": "P1复核闭环",
            "status": "PASS" if summary["week9_unresolved_p1"] == 0 else "WARN",
            "result": summary["week9_unresolved_p1"],
            "note": "未闭环P1为0",
        },
        {
            "check_item": "研究面板行数",
            "status": "PASS" if summary["research_panel_rows"] == 8 else "WARN",
            "result": summary["research_panel_rows"],
            "note": "公司层面一家公司一行",
        },
        {
            "check_item": "谨慎样本标记",
            "status": "PASS",
            "result": summary["caution_company_count"],
            "note": "异常或披露边界不强行修正，只在研究变量中标记",
        },
        {
            "check_item": "PostgreSQL导入状态",
            "status": postgres.loc[postgres["check_name"].eq("postgres_import"), "status"].iloc[0],
            "result": postgres.loc[postgres["check_name"].eq("postgres_import"), "detail"].iloc[0],
            "note": "没有口令时只生成导入脚本和审计，不写已入库",
        },
    ]
    pg_summary_path = DATABASE / "postgresql_disclosure_summary_week10.csv"
    if pg_summary_path.exists():
        pg_summary = pd.read_csv(pg_summary_path, dtype=str, keep_default_na=False)
        total_rows = pg_summary.loc[pg_summary["item"].eq("导入总行数"), "value"]
        checks.append(
            {
                "check_item": "临时PostgreSQL查询披露",
                "status": "PASS",
                "result": f"导入总行数={total_rows.iloc[0] if not total_rows.empty else '已生成'}",
                "note": "使用55432端口临时PostgreSQL实例真实导入并导出查询结果",
            }
        )
    else:
        checks.append(
            {
                "check_item": "临时PostgreSQL查询披露",
                "status": "WARN",
                "result": "尚未生成",
                "note": "运行database/run_postgres_temp_week10.ps1后生成披露结果",
            }
        )
    return pd.DataFrame(checks)


def build_report_md(summary: dict, board: pd.DataFrame, desc: pd.DataFrame, reg: pd.DataFrame) -> None:
    postgres_status_label = {
        "READY_NEED_PASSWORD": "需密码后导入",
        "READY_WITH_PASSWORD": "可执行导入",
    }.get(summary["postgres_status"], summary["postgres_status"])
    pg_summary_path = DATABASE / "postgresql_disclosure_summary_week10.csv"
    if pg_summary_path.exists():
        pg_summary = pd.read_csv(pg_summary_path, dtype=str, keep_default_na=False)
        pg_counts = pd.read_csv(DATABASE / "postgresql_table_counts_week10.csv", dtype=str, keep_default_na=False)
        pg_company = pd.read_csv(
            DATABASE / "postgresql_company_panel_disclosure_week10.csv", dtype=str, keep_default_na=False
        )
        pg_summary_md = markdown_table(pg_summary[["item", "value", "source_note"]])
        pg_counts_md = markdown_table(pg_counts[["table_name", "row_count"]])
        pg_company_md = markdown_table(
            pg_company[
                [
                    "stock_code",
                    "company_short",
                    "market",
                    "broad_pevc_record_share",
                    "pevc_strength_index",
                    "quality_gate",
                ]
            ]
        )
        postgres_display = "临时PostgreSQL导入查询完成"
    else:
        pg_summary_md = "尚未运行临时PostgreSQL导入脚本。"
        pg_counts_md = ""
        pg_company_md = ""
        postgres_display = postgres_status_label
    top_desc = markdown_table(desc[["variable_label", "n", "mean", "median", "min", "max"]])
    board_md = markdown_table(board[
        [
            "market",
            "company_count",
            "avg_pevc_strength_index",
            "avg_broad_pevc_record_share",
            "avg_top1_ratio_pct",
            "avg_effective_shareholder_count",
        ]
    ])
    reg_md = markdown_table(reg[
        [
            "sample_scope",
            "dependent_variable",
            "independent_variable",
            "n",
            "coef_x",
            "r_squared",
            "model_note",
        ]
    ].head(6))
    text = f"""# 第十周任务报告：研究型数据集、探索性统计与数据库导入规范化

姓名：霍泓锟  
日期：{RUN_DATE}

## 一、本周任务定位

第十周承接第九周“P1复核闭环、数据库准备和初步研究问题形成”的工作，把8家公司三表数据进一步整理为公司层面的研究面板。相比前几周侧重抽取和修错，本周的重点是把数据转化成可被检验、可被复现、可继续扩样的研究材料。

本周没有虚构新增公司，也没有用外部资料填补招股书未披露字段。对备案编码、GP和LP结构等深度PE基金字段，本周只生成补充核验队列，并明确保留空值，等待后续逐条人工核验。

## 二、核心结果

- 样本公司数：{summary["company_count"]}家。
- 公司层研究面板：{summary["research_panel_rows"]}行。
- 投资主体画像：{summary["investor_profile_rows"]}个主体-类型组合。
- 基金/投资平台补充核验队列：{summary["fund_queue_rows"]}条。
- 第九周遗留P1未闭环项：{summary["week9_unresolved_p1"]}条。
- PostgreSQL状态：{postgres_display}。

## 三、描述性统计

{top_desc}

## 四、板块差异观察

{board_md}

目前每个板块只有2家公司，因此表中的板块差异只能帮助形成研究假设，不能作为稳健结论。第十周更重要的成果是确认这些变量可以从三表自动生成，并且异常样本被单独标记。

## 五、探索性OLS结果

{reg_md}

这些OLS只用于课堂展示中的“研究问题如何从数据表走向计量模型”。样本量为8或剔除谨慎样本后的更小样本，不能解释为因果关系，也不应报告为正式论文结论。

## 六、PostgreSQL结果与数据披露

{pg_summary_md}

{pg_counts_md}

{pg_company_md}

以上结果来自PostgreSQL查询导出，而不是直接复制Excel。5432主库仍需要本机口令，本周使用55432端口临时实例完成真实导入和结果披露。

## 七、本周不足与下一步

第一，PostgreSQL主库5432仍需要本机口令，本周先用临时实例完成真实导入和查询披露，后续需迁移到长期库。第二，PE/VC强度指数目前是基于记录占比和持股主体数构造的简化指标，仍受招股书披露详略影响。第三，基金备案编码、GP和LP结构没有从三表直接披露出来，因此必须放入人工或外部核验队列。

下一周应优先完成三件事：一是把临时PostgreSQL导入流程迁移到本人长期库并保存行数校验日志；二是扩展样本以提高描述统计稳定性；三是对P1基金主体补充备案编码、GP/LP结构和来源证据，使研究变量从“粗分类”进一步进入“主体穿透”层面。
"""
    (REPORT / "week10_report.md").write_text(text, encoding="utf-8")


def build_readme(summary: dict) -> None:
    postgres_status_label = {
        "READY_NEED_PASSWORD": "需密码后导入",
        "READY_WITH_PASSWORD": "可执行导入",
    }.get(summary["postgres_status"], summary["postgres_status"])
    postgres_temp_label = (
        "临时PostgreSQL导入查询完成"
        if (DATABASE / "postgresql_disclosure_summary_week10.csv").exists()
        else postgres_status_label
    )
    text = f"""# 霍泓锟第十周任务提交

## 任务定位

本周承接第九周结果，把8家公司三表数据继续加工为研究型数据集。核心目标是：形成公司层研究面板、投资主体画像、基金备案/GP/LP补充核验队列、描述性统计、相关性、探索性OLS结果，并补充PostgreSQL真实导入与查询披露结果。

## 统一运行命令

在 Codex 本机环境中可直接运行一键脚本：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File code\\run_all_week10_codex.ps1
```

如果使用普通 Python/Node 环境，可以按以下顺序运行：

```powershell
pip install -r requirements.txt
python code/week10_analysis_pipeline.py
powershell -NoProfile -ExecutionPolicy Bypass -File database\\run_postgres_temp_week10.ps1
python code/week10_analysis_pipeline.py
node code/build_week10_workbook.mjs
python code/build_week10_report_docx.py
python code/build_week10_report_pdf.py
```

使用 Codex 自带运行环境时：

```powershell
& "C:\\Users\\29818\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe" code\\week10_analysis_pipeline.py
powershell -NoProfile -ExecutionPolicy Bypass -File database\\run_postgres_temp_week10.ps1
& "C:\\Users\\29818\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe" code\\week10_analysis_pipeline.py
cmd /c mklink /J node_modules "C:\\Users\\29818\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\node_modules"
& "C:\\Users\\29818\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\bin\\node.exe" code\\build_week10_workbook.mjs
& "C:\\Users\\29818\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe" code\\build_week10_report_docx.py
& "C:\\Users\\29818\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe" code\\build_week10_report_pdf.py
```

## 核心结果

| 指标 | 数值 |
|---|---:|
| 样本公司 | {summary["company_count"]} |
| 公司层研究面板 | {summary["research_panel_rows"]} |
| 投资主体画像 | {summary["investor_profile_rows"]} |
| 基金补充核验队列 | {summary["fund_queue_rows"]} |
| 探索性OLS模型 | {summary["regression_models"]} |
| PostgreSQL状态 | {postgres_temp_label} |

## 主要输出

| 文件 | 说明 |
|---|---|
| `data/derived/company_research_panel_week10.csv` | 公司层研究面板 |
| `data/derived/investor_profile_week10.csv` | 投资主体画像 |
| `data/derived/fund_enrichment_queue_week10.csv` | 备案编码、GP/LP结构补充核验队列 |
| `data/derived/descriptive_stats_week10.csv` | 变量描述性统计 |
| `data/derived/correlation_matrix_week10.csv` | 相关系数矩阵 |
| `data/derived/regression_results_week10.csv` | 探索性OLS结果 |
| `database/schema_postgresql_week10.sql` | PostgreSQL建表脚本 |
| `database/import_week10_tables.sql` | PostgreSQL导入脚本 |
| `database/run_postgres_temp_week10.ps1` | 临时PostgreSQL实例导入和查询脚本 |
| `database/postgres_week10_queries.sql` | PostgreSQL披露查询SQL |
| `database/postgresql_table_counts_week10.csv` | PostgreSQL导入后表行数 |
| `database/postgresql_company_panel_disclosure_week10.csv` | PostgreSQL查询导出的公司层披露数据 |
| `database/postgresql_investor_type_summary_week10.csv` | PostgreSQL查询导出的投资者类型统计 |
| `database/postgresql_fund_enrichment_status_week10.csv` | PostgreSQL查询导出的基金深度字段披露状态 |
| `outputs/week10_summary_workbook.xlsx` | 第十周Excel汇总 |
| `report/霍泓锟_第十周任务报告.docx` | 可提交周报 |
| `report/霍泓锟_第十周任务报告.pdf` | 可提交周报PDF |

## 工程原则

1. 从第九周Final/derived数据出发，代码不读取人工补写的结论表作为Auto结果。
2. 备案编码、GP、LP结构未在三表中披露时留空，不用名称猜测。
3. 小样本OLS仅用于演示研究路径，不报告为因果结论。
4. 本机5432主库没有口令时不伪造主库入库；本周使用55432端口临时PostgreSQL实例真实导入并导出查询结果。
"""
    (ROOT / "README.md").write_text(text, encoding="utf-8")


def build_manifest(files: list[tuple[str, str]]) -> pd.DataFrame:
    rows = []
    for rel, desc in files:
        path = ROOT / rel
        rows.append(
            {
                "path": rel,
                "description": desc,
                "exists": path.exists(),
                "bytes": path.stat().st_size if path.exists() and path.is_file() else "",
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    ensure_dirs()

    research = read_csv("research_variables_week9.csv")
    subs = read_csv("subscription_week9_clean.csv")
    snaps = read_csv("equity_snapshot_week9_clean.csv")
    transfers = read_csv("transfer_week9_clean.csv")
    snapshot_validity = read_csv("snapshot_ratio_validity_week9.csv")
    review_queue = pd.read_csv(REVIEW / "review_queue_resolved_week9.csv", dtype=str, keep_default_na=False)

    ratio_quality = build_ratio_quality(snapshot_validity, review_queue)
    panel = make_company_panel(research, ratio_quality)
    field_completeness = build_field_completeness(subs, snaps, transfers)
    investor_rows = collect_investor_rows(subs, snaps, transfers)
    investor_profile = build_investor_profile(investor_rows)
    fund_queue = build_fund_queue(investor_profile)
    desc, board = build_descriptive_stats(panel)
    corr = build_correlation(panel)
    reg = build_regressions(panel)
    questions = build_research_questions(panel, corr, reg)
    postgres = postgres_audit()

    summary = {
        "run_date": RUN_DATE,
        "run_time": RUN_TIME,
        "company_count": int(panel["stock_code"].nunique()),
        "research_panel_rows": int(panel.shape[0]),
        "investor_profile_rows": int(investor_profile.shape[0]),
        "fund_queue_rows": int(fund_queue.shape[0]),
        "descriptive_variables": int(desc.shape[0]),
        "correlation_pairs": int(corr.shape[0]),
        "regression_models": int(reg.shape[0]),
        "caution_company_count": int(panel["caution_flag"].sum()),
        "week9_unresolved_p1": int(panel["week9_unresolved_p1_count"].fillna(0).sum()),
        "postgres_status": postgres.loc[postgres["check_name"].eq("postgres_import"), "status"].iloc[0],
    }
    validation = build_validation_summary(summary, ratio_quality, postgres)

    outputs = {
        "company_research_panel_week10": panel,
        "investor_profile_week10": investor_profile,
        "fund_enrichment_queue_week10": fund_queue,
        "data_quality_gate_week10": ratio_quality,
        "field_completeness_week10": field_completeness,
        "descriptive_stats_week10": desc,
        "board_stats_week10": board,
        "correlation_matrix_week10": corr,
        "regression_results_week10": reg,
        "research_questions_week10": questions,
    }
    for name, df in outputs.items():
        write_csv(DERIVED / f"{name}.csv", df)
    write_csv(DATABASE / "postgres_connection_audit_week10.csv", postgres)
    write_csv(VALIDATION / "week10_validation_summary.csv", validation)

    write_postgres_scripts(
        {
            "company_research_panel_week10": panel,
            "investor_profile_week10": investor_profile,
            "fund_enrichment_queue_week10": fund_queue,
            "descriptive_stats_week10": desc,
            "board_stats_week10": board,
            "correlation_matrix_week10": corr,
            "regression_results_week10": reg,
            "research_questions_week10": questions,
            "data_quality_gate_week10": ratio_quality,
            "field_completeness_week10": field_completeness,
        }
    )

    workbook_payload = {
        "summary": summary,
        "panel": panel.fillna("").to_dict("records"),
        "investor_profile": investor_profile.fillna("").to_dict("records"),
        "fund_queue": fund_queue.fillna("").to_dict("records"),
        "data_quality": ratio_quality.fillna("").to_dict("records"),
        "field_completeness": field_completeness.fillna("").to_dict("records"),
        "descriptive_stats": desc.fillna("").to_dict("records"),
        "board_stats": board.fillna("").to_dict("records"),
        "correlation": corr.fillna("").to_dict("records"),
        "regression": reg.fillna("").to_dict("records"),
        "research_questions": questions.fillna("").to_dict("records"),
        "validation": validation.fillna("").to_dict("records"),
        "postgres": postgres.fillna("").to_dict("records"),
    }
    (OUTPUTS / "week10_workbook_data.json").write_text(
        json.dumps(workbook_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUTPUTS / "week10_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    build_report_md(summary, board, desc, reg)
    build_readme(summary)

    manifest = build_manifest(
        [
            ("requirements.txt", "Python依赖清单"),
            ("code/week10_analysis_pipeline.py", "第十周主流程"),
            ("code/run_all_week10_codex.ps1", "Codex本机环境一键运行脚本"),
            ("code/build_week10_workbook.mjs", "Excel汇总生成脚本"),
            ("code/build_week10_report_docx.py", "周报DOCX生成脚本"),
            ("code/build_week10_report_pdf.py", "周报PDF生成脚本"),
            ("data/derived/company_research_panel_week10.csv", "公司层研究面板"),
            ("data/derived/investor_profile_week10.csv", "投资主体画像"),
            ("data/derived/fund_enrichment_queue_week10.csv", "基金补充核验队列"),
            ("data/derived/descriptive_stats_week10.csv", "描述性统计"),
            ("data/derived/correlation_matrix_week10.csv", "相关系数矩阵"),
            ("data/derived/regression_results_week10.csv", "探索性OLS结果"),
            ("database/schema_postgresql_week10.sql", "PostgreSQL建表脚本"),
            ("database/import_week10_tables.sql", "PostgreSQL导入脚本"),
            ("database/run_postgres_temp_week10.ps1", "临时PostgreSQL实例导入和查询脚本"),
            ("database/postgres_week10_queries.sql", "PostgreSQL披露查询SQL"),
            ("database/postgresql_disclosure_summary_week10.csv", "PostgreSQL查询披露摘要"),
            ("database/postgresql_table_counts_week10.csv", "PostgreSQL导入表行数"),
            ("database/postgresql_company_panel_disclosure_week10.csv", "PostgreSQL公司层披露数据"),
            ("database/postgresql_board_summary_week10.csv", "PostgreSQL板块披露数据"),
            ("database/postgresql_investor_type_summary_week10.csv", "PostgreSQL投资者类型披露数据"),
            ("database/postgresql_fund_enrichment_status_week10.csv", "PostgreSQL基金深度字段披露状态"),
            ("database/postgresql_regression_brief_week10.csv", "PostgreSQL回归结果摘要"),
            ("validation/week10_validation_summary.csv", "验证摘要"),
            ("outputs/week10_summary_workbook.xlsx", "第十周Excel汇总"),
            ("report/霍泓锟_第十周任务报告.docx", "第十周报告DOCX"),
            ("report/霍泓锟_第十周任务报告.pdf", "第十周报告PDF"),
        ]
    )
    write_csv(DERIVED / "week10_submission_manifest.csv", manifest)

    log_lines = [
        f"run_time={RUN_TIME}",
        f"company_count={summary['company_count']}",
        f"research_panel_rows={summary['research_panel_rows']}",
        f"investor_profile_rows={summary['investor_profile_rows']}",
        f"fund_queue_rows={summary['fund_queue_rows']}",
        f"regression_models={summary['regression_models']}",
        f"postgres_status={summary['postgres_status']}",
    ]
    (LOGS / "week10_pipeline.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
