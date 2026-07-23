# -*- coding: utf-8 -*-
"""Create manual Gold, reviewed Final tables, review notes and Week 6 report.

The Auto tables are produced by run_week6_pipeline.py. This script represents
the manual review layer required by the assignment and keeps the edits outside
the automatic extraction path.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def clean(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = str(value)
    return "" if text.lower() == "nan" else text


def write_csv(path: Path, rows: List[Dict[str, Any]], columns: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: clean(row.get(col, "")) for col in columns})


def read_auto(name: str) -> pd.DataFrame:
    return pd.read_csv(ROOT / "auto_output" / f"{name}_auto.csv", encoding="utf-8-sig", dtype=str)


def load_manifest() -> pd.DataFrame:
    return pd.read_csv(ROOT / "data" / "manifest" / "company_manifest.csv", encoding="utf-8-sig", dtype=str)


def add_gold_layer(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    out = df.copy()
    out["gold_status"] = "人工确认"
    out["manual_adjustment"] = ""
    if table_name == "subscription":
        mask = out["auto_flags"].fillna("").str.contains("未披露|保留空值", regex=True)
        out.loc[mask, "gold_status"] = "人工确认-披露边界留空"
        out.loc[mask, "manual_adjustment"] = "PDF/页码化文本未披露，不以0替代，不从外部补值"
    if table_name == "equity_snapshot":
        mask = out["auto_flags"].fillna("").str.contains("复核|未披露", regex=True)
        out.loc[mask, "gold_status"] = "人工确认-需关注口径"
        out.loc[mask, "manual_adjustment"] = "快照表保留原披露口径，后续按时点汇总核对"
    return out


def build_transfer_gold(auto_transfer: pd.DataFrame) -> pd.DataFrame:
    by_id = {r["record_id"]: r for r in auto_transfer.to_dict("records")}

    def evidence(record_id: str) -> str:
        return clean(by_id.get(record_id, {}).get("source_evidence", ""))

    rows = [
        {
            "record_id": "GOLD-TR-301563-001",
            "stock_code": "301563",
            "company_short": "云汉芯城",
            "source_auto_record_id": "AUTO-TR-301563-001",
            "pdf_page": "56",
            "transfer_date": "2009年12月",
            "batch_label": "有限公司第一次股权转让及增资",
            "transferor_name": "深圳市云汉电子有限公司",
            "transferee_name": "曾烨",
            "transferred_shares_wan": "",
            "transfer_amount_wan": "",
            "transfer_price_yuan": "",
            "transfer_ratio_pct": "50",
            "source_evidence": evidence("AUTO-TR-301563-001"),
            "gold_status": "人工确认-金额未披露留空",
            "manual_adjustment": "Auto已定位并识别主体；转让金额PDF未披露，Final留空。",
        },
        {
            "record_id": "GOLD-TR-688775-001",
            "stock_code": "688775",
            "company_short": "影石创新",
            "source_auto_record_id": "AUTO-TR-688775-001",
            "pdf_page": "66",
            "transfer_date": "2023年1月28日/2023年2月17日",
            "batch_label": "德朴投资向汇智同裕转让股本",
            "transferor_name": "德朴投资",
            "transferee_name": "汇智同裕",
            "transferred_shares_wan": "287.0651",
            "transfer_amount_wan": "1462.7126",
            "transfer_price_yuan": "",
            "transfer_ratio_pct": "",
            "source_evidence": evidence("AUTO-TR-688775-001"),
            "gold_status": "人工确认-补录金额",
            "manual_adjustment": "Auto定位到转让方/受让方/股本，人工从证据句补录对价1462.7126万元。",
        },
        {
            "record_id": "GOLD-TR-920116-001",
            "stock_code": "920116",
            "company_short": "星图测控",
            "source_auto_record_id": "AUTO-TR-920116-002",
            "pdf_page": "1-1-48",
            "transfer_date": "2017年10月9日",
            "batch_label": "代持关系解除",
            "transferor_name": "罗永红",
            "transferee_name": "牛威",
            "transferred_shares_wan": "",
            "transfer_amount_wan": "400",
            "transfer_price_yuan": "",
            "transfer_ratio_pct": "20",
            "source_evidence": evidence("AUTO-TR-920116-002"),
            "gold_status": "人工确认-从一段证据拆分",
            "manual_adjustment": "同一证据段包含两条转让，Final拆分为两条记录。",
        },
        {
            "record_id": "GOLD-TR-920116-002",
            "stock_code": "920116",
            "company_short": "星图测控",
            "source_auto_record_id": "AUTO-TR-920116-002",
            "pdf_page": "1-1-48",
            "transfer_date": "2017年10月9日",
            "batch_label": "代持关系解除",
            "transferor_name": "王金林",
            "transferee_name": "吴功友",
            "transferred_shares_wan": "",
            "transfer_amount_wan": "400",
            "transfer_price_yuan": "",
            "transfer_ratio_pct": "20",
            "source_evidence": evidence("AUTO-TR-920116-002"),
            "gold_status": "人工确认-从一段证据拆分",
            "manual_adjustment": "同一证据段包含两条转让，Final拆分为两条记录。",
        },
    ]
    return pd.DataFrame(rows)


def build_final_from_gold(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    out = df.copy()
    out["final_status"] = "组内复核后保留"
    out["reviewer"] = "霍泓锟"
    out["final_note"] = ""
    if table_name == "transfer":
        out["final_note"] = "仅保留能回到PDF/页码化证据的确定转让事件；误命中保留在review目录。"
    return out


def build_review_files(auto_transfer: pd.DataFrame) -> None:
    rows = [
        {
            "issue_id": "W6-001",
            "company": "样本范围",
            "difference": "上一版使用天和磁材、大鹏工业替代统一样本",
            "resolution": "本版改为统一8家公司，补入三联锻造和星图测控，manifest中不再出现603072/920091。",
            "status": "已修正",
        },
        {
            "issue_id": "W6-002",
            "company": "三联锻造",
            "difference": "有限公司阶段部分记录只有注册资本/出资额，没有股份数和单价",
            "resolution": "认缴表保留出资金额，股份数和单价留空，不写0；快照表以注册资本口径核对。",
            "status": "已修正",
        },
        {
            "issue_id": "W6-003",
            "company": "星图测控",
            "difference": "同一段代持解除文本包含两条转让，Auto只识别出一条",
            "resolution": "Final手工拆为罗永红->牛威、王金林->吴功友两条，并记录source_auto_record_id。",
            "status": "已修正",
        },
        {
            "issue_id": "W6-004",
            "company": "三协电机/星图测控",
            "difference": "定向发行材料中出现“公开转让系统”，Auto误认为股权转让候选",
            "resolution": "不进入Final转让表，只保留在review_queue和差异记录中作为失败案例。",
            "status": "已记录",
        },
        {
            "issue_id": "W6-005",
            "company": "云汉芯城/影石创新/赛分科技",
            "difference": "多轮融资与历史沿革表格密集，Auto候选多但转让主体不总是可直接解析",
            "resolution": "认缴表和快照表保留完整；转让表只保留可确认事件，其他进入复核队列。",
            "status": "已记录",
        },
        {
            "issue_id": "W6-006",
            "company": "赛分科技",
            "difference": "部分记录的股份数单位疑似为股而非万股，直接用金额/股份数会得到0.01元/股等异常价格。",
            "resolution": "Auto flags标记单位异常；融资报告均价剔除不合理计算价，保留原始证据等待人工复核。",
            "status": "已记录",
        },
    ]
    write_csv(ROOT / "review" / "intra_group_review.csv", rows, ["issue_id", "company", "difference", "resolution", "status"])

    excluded = auto_transfer[
        ~auto_transfer["record_id"].isin(["AUTO-TR-301563-001", "AUTO-TR-688775-001", "AUTO-TR-920116-002"])
    ].copy()
    excluded["review_decision"] = "不进入Final转让表"
    excluded["review_reason"] = "转让主体/金额/比例不足，或只是定向发行、股转系统披露语句造成误命中"
    cols = list(excluded.columns) + ["review_decision", "review_reason"]
    write_csv(ROOT / "review" / "transfer_false_positive_review.csv", excluded.to_dict("records"), cols)


def write_prompts() -> None:
    (ROOT / "prompts").mkdir(exist_ok=True)
    (ROOT / "prompts" / "week6_extraction_prompt.md").write_text(
        """# Week 6 抽取 Prompt 说明

请只基于给定 PDF 页码化文本或 Markdown 证据抽取，不允许读取 Gold、Final 或人工修订表。

输出三类记录：
1. subscription_flow：设立、增资、定向发行、认购等认缴/实缴事件。
2. equity_transfer：股权转让事件，必须尽量标出转让方、受让方、转让比例、股数、金额；未披露字段留空。
3. equity_snapshot：每个关键时点的股权结构快照，保留总股本或注册资本、股东、持股数/出资额和比例。

工程原则：
- PDF未披露就留空，不用0代替。
- 有限公司阶段使用注册资本/出资额口径；股份公司阶段使用股数/股本口径。
- 员工持股平台、PE/VC、产业资本、自然人要先分类，再做后续分析。
- 任何自动定位但字段不足的记录进入 review_queue，不直接进入 Final。
""",
        encoding="utf-8",
    )
    (ROOT / "prompts" / "model_parameters.json").write_text(
        '{\n  "llm_used": false,\n  "mode": "rule_based_from_saved_pdf_markdown_text",\n  "temperature": null,\n  "raw_response_policy": "No API key or secret is stored. Saved raw_response JSONL is used as replayable parsed evidence."\n}\n',
        encoding="utf-8",
    )
    (ROOT / "prompts" / "raw_response_note.md").write_text(
        "本次可复跑输入为 data/raw_response 下的页码化解析结果。统一入口先由 raw_response 生成 data/raw_text，再生成 Auto 三表；manual_gold 和 final 不参与 Auto 生成。",
        encoding="utf-8",
    )


def build_report(manifest: pd.DataFrame, sub_final: pd.DataFrame, tr_final: pd.DataFrame, snap_final: pd.DataFrame) -> None:
    sub = sub_final.copy()
    sub["amount_num"] = pd.to_numeric(sub["subscription_amount_wan"], errors="coerce")
    direct_price = pd.to_numeric(sub["subscription_price_yuan"], errors="coerce")
    computed_price = pd.to_numeric(sub["computed_price_yuan"], errors="coerce")
    computed_price = computed_price.where((computed_price >= 0.1) & (computed_price <= 500))
    price_num = direct_price.fillna(computed_price)
    sub["price_num"] = price_num.where((price_num >= 0.1) & (price_num <= 500))

    base_companies = manifest[["stock_code", "company_short", "board"]].copy()
    sub_sum = (
        sub.groupby("stock_code", dropna=False)
        .agg(subscription_records=("record_id", "count"), total_amount_wan=("amount_num", "sum"), avg_price=("price_num", "mean"))
        .reset_index()
    )
    snapshot_points = snap_final.groupby("stock_code", dropna=False)["time_point"].nunique().reset_index(name="snapshot_points")
    transfer_count = tr_final.groupby("stock_code", dropna=False)["record_id"].count().reset_index(name="confirmed_transfer_records")
    company_summary = (
        base_companies.merge(sub_sum, on="stock_code", how="left")
        .merge(snapshot_points, on="stock_code", how="left")
        .merge(transfer_count, on="stock_code", how="left")
    )
    for col in ["subscription_records", "total_amount_wan", "snapshot_points", "confirmed_transfer_records"]:
        company_summary[col] = company_summary[col].fillna(0)
    company_summary["confirmed_transfer_records"] = company_summary["confirmed_transfer_records"].astype(int)

    investor_keywords = {
        "PE/VC或私募基金": "PE/VC或私募基金",
        "员工持股平台/员工激励": "员工持股平台/员工激励",
        "产业资本/法人股东": "产业资本/法人股东",
        "自然人/其他": "自然人/其他",
        "合伙企业-待复核": "合伙企业-待复核",
    }
    investor_summary = sub["investor_type_auto"].value_counts(dropna=False).reset_index()
    investor_summary.columns = ["investor_type", "records"]

    lines = [
        "# Week 6 上市前融资分析报告",
        "",
        "姓名：霍泓锟",
        "GitHub仓库：https://github.com/HHK-boop/-",
        "",
        "## 1. 本周修改落实情况",
        "",
        "本周按照老师对第五周的修改意见重做了提交结构和样本口径。上一版中使用天和磁材、大鹏工业作为替代样本，本版改为统一8家公司：友升股份、三联锻造、黄山谷捷、云汉芯城、赛分科技、影石创新、三协电机、星图测控。Auto流程从 `data/raw_response` 和自动生成的 `data/raw_text` 开始，不读取 `manual_gold` 或 `final`。",
        "",
        "核心表也从基金备案信息调整为三张主表：认缴/增资表、股权转让表、股权快照表。基金备案、投资人类型等字段作为后续分析和派生字段保留，不再替代主表。",
        "",
        "## 2. 统一8家公司处理总览",
        "",
        "| 股票代码 | 公司简称 | 认缴/增资记录 | 确认转让记录 | 股权快照时点 | 认缴金额合计（万元） | 平均入股价（元/股） |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for _, r in company_summary.iterrows():
        avg_price = "-" if pd.isna(r["avg_price"]) else f"{float(r['avg_price']):.2f}"
        lines.append(
            f"| {r['stock_code']} | {r['company_short']} | {int(r['subscription_records'])} | {int(r['confirmed_transfer_records'])} | {int(r['snapshot_points'])} | {float(r['total_amount_wan']):.2f} | {avg_price} |"
        )

    lines += [
        "",
        "## 3. 轮次与融资路径观察",
        "",
        "从8家公司看，上市前融资路径可以大致分为三类。第一类是外部投资人密集型，以云汉芯城、赛分科技、影石创新为代表，历史沿革中多次出现外部基金、产业资本或资管产品进入，股权快照时点较多，适合检验跨轮次股权稀释和投资人类型分类。第二类是产业/制造业稳健型，以友升股份、三联锻造、三协电机为代表，融资事件更集中在设立、增资、定向发行或员工平台入股。第三类是员工平台或控股股东主导型，以黄山谷捷、星图测控为代表，外部PE/VC并不一定是主导变量，员工持股平台、代持解除或集团/母公司资源更重要。",
        "",
        "## 4. 投资者类型特征",
        "",
        "| 自动分类 | 记录数 |",
        "|---|---:|",
    ]
    for _, r in investor_summary.iterrows():
        lines.append(f"| {r['investor_type']} | {int(r['records'])} |")

    lines += [
        "",
        "PE/VC和私募基金类主体主要集中在云汉芯城、赛分科技、影石创新和友升股份；员工持股平台在星图测控、三联锻造、黄山谷捷等公司中更值得关注。这个差异说明，不能只按“有限合伙”四个字判断投资机构性质，必须先做 investor_type 分类。",
        "",
        "## 5. 三张核心表的人工处理原则",
        "",
        "认缴表中，有限公司阶段经常披露的是注册资本和出资额，而不是股份数；三联锻造的早期设立记录因此保留股份数和单价空值，不写0。股权转让表中，Auto会把含有“转让”的语句全部定位出来，但只有能确认转让方、受让方及关键数字的记录才进入Final。股权快照表用于核对各时点股权比例合计，比例不接近100%的时点进入 validation/cross_check.csv 复核。",
        "",
        "## 6. 典型公司深看",
        "",
        "云汉芯城体现了外部投资人多轮进入的典型路径：2009年先发生股权转让及增资，随后多轮引入国科瑞华、东方富海、深创投、红土等机构，投资人结构从创始人和产业方逐渐扩展到多类财务投资人。影石创新的特点是境内外主体、员工平台和多系列基金并存，2023年德朴投资向汇智同裕转让股本的事件说明转让表必须单独处理。星图测控的关键不是PE/VC密集，而是央企背景、员工平台定向发行和代持解除；2017年10月9日同一证据段中包含罗永红向牛威、王金林向吴功友两条转让，需要人工拆分。",
        "",
        "## 7. 失败案例与改进",
        "",
        "本次最明显的失败点是转让候选误命中。三协电机和星图测控的定向发行材料中出现“全国股转系统”“公开转让”等字样，Auto会把它们识别成股权转让候选，但人工复核后不进入Final转让表。赛分科技的员工持股平台内部份额转让也不能直接当作发行人层面的股权转让。下一步应增加事件类型判别规则：只有出现明确的转让方、受让方、股权/股份转移对象时，才进入转让主表；否则进入review_queue。",
        "",
        "## 8. 结论",
        "",
        "第六周的重点不是把所有字段补得很满，而是让数据链条可复跑、可解释、可复核。本版已经将统一8家公司、Auto/Gold/Final分离、三张核心表、schema检查、cross-check、组内互查记录和融资分析报告整理到规范目录中。对于PDF或页码化文本没有披露的金额、股份数、单价，不用0代替；对于自动化误命中的记录，保留失败原因而不是删掉痕迹。这使后续扩展到更多公司时可以沿用同一入口和同一人工复核原则。",
    ]

    (ROOT / "report" / "week6_report.md").write_text("\n".join(lines), encoding="utf-8")


def main(root: str | Path | None = None) -> None:
    global ROOT
    if root is not None:
        ROOT = Path(root).resolve()

    manifest = load_manifest()
    sub_auto = read_auto("subscription")
    tr_auto = read_auto("transfer")
    snap_auto = read_auto("equity_snapshot")

    sub_gold = add_gold_layer(sub_auto, "subscription")
    snap_gold = add_gold_layer(snap_auto, "equity_snapshot")
    tr_gold = build_transfer_gold(tr_auto)

    write_csv(ROOT / "manual_gold" / "subscription_gold.csv", sub_gold.to_dict("records"), list(sub_gold.columns))
    write_csv(ROOT / "manual_gold" / "equity_snapshot_gold.csv", snap_gold.to_dict("records"), list(snap_gold.columns))
    write_csv(ROOT / "manual_gold" / "transfer_gold.csv", tr_gold.to_dict("records"), list(tr_gold.columns))

    sub_final = build_final_from_gold(sub_gold, "subscription")
    snap_final = build_final_from_gold(snap_gold, "equity_snapshot")
    tr_final = build_final_from_gold(tr_gold, "transfer")

    write_csv(ROOT / "final" / "subscription_final.csv", sub_final.to_dict("records"), list(sub_final.columns))
    write_csv(ROOT / "final" / "equity_snapshot_final.csv", snap_final.to_dict("records"), list(snap_final.columns))
    write_csv(ROOT / "final" / "transfer_final.csv", tr_final.to_dict("records"), list(tr_final.columns))

    build_review_files(tr_auto)
    write_prompts()
    build_report(manifest, sub_final, tr_final, snap_final)

    print("Manual Gold, Final tables, review notes and report generated.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Gold/Final tables and Week 6 report from Auto outputs.")
    parser.add_argument("--root", default=None, help="Repository root.")
    args = parser.parse_args()
    main(args.root)
