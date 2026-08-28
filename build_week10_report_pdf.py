"""Build a PDF version of the Week 10 report."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
DATABASE = ROOT / "database"
REPORT = ROOT / "report"
OUTPUT = REPORT / "霍泓锟_第十周任务报告.pdf"
RUN_DATE = "2026年8月26日"


def register_font() -> str:
    candidates = [
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\simsun.ttc"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
    ]
    for font in candidates:
        if font.exists():
            pdfmetrics.registerFont(TTFont("CNFont", str(font)))
            return "CNFont"
    return "Helvetica"


FONT = register_font()


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DERIVED / name, dtype=str, keep_default_na=False)


def read_database_csv(name: str) -> pd.DataFrame:
    path = DATABASE / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontName=FONT,
            fontSize=18,
            leading=24,
            textColor=colors.HexColor("#17365D"),
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "meta": ParagraphStyle(
            "meta",
            parent=base["Normal"],
            fontName=FONT,
            fontSize=10,
            leading=14,
            alignment=TA_CENTER,
            spaceAfter=14,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName=FONT,
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1F4D78"),
            spaceBefore=8,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName=FONT,
            fontSize=9.5,
            leading=14,
            alignment=TA_LEFT,
            spaceAfter=6,
        ),
        "cell": ParagraphStyle(
            "cell",
            parent=base["Normal"],
            fontName=FONT,
            fontSize=7.4,
            leading=10,
            alignment=TA_LEFT,
        ),
    }


S = styles()


def p(text: object, style: str = "cell") -> Paragraph:
    return Paragraph("" if text is None else str(text), S[style])


def display_status(value: str) -> str:
    return {
        "READY_NEED_PASSWORD": "需密码后导入",
        "READY_WITH_PASSWORD": "可执行导入",
    }.get(str(value), str(value))


def add_table(story, headers: list[str], rows: list[list[object]], widths: list[float]) -> None:
    data = [[p(h) for h in headers]]
    for row in rows:
        data.append([p(v) for v in row])
    table = Table(data, colWidths=[w * mm for w in widths], repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0B2545")),
                ("FONTNAME", (0, 0), (-1, -1), FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 7.4),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D0D7DE")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 5))


def main() -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    panel = read_csv("company_research_panel_week10.csv")
    board = read_csv("board_stats_week10.csv")
    fund_queue = read_csv("fund_enrichment_queue_week10.csv")
    reg = read_csv("regression_results_week10.csv")
    validation = pd.read_csv(ROOT / "validation" / "week10_validation_summary.csv", dtype=str, keep_default_na=False)
    postgres = pd.read_csv(DATABASE / "postgres_connection_audit_week10.csv", dtype=str, keep_default_na=False)
    pg_summary = read_database_csv("postgresql_disclosure_summary_week10.csv")
    pg_counts = read_database_csv("postgresql_table_counts_week10.csv")
    pg_company = read_database_csv("postgresql_company_panel_disclosure_week10.csv")
    pg_investor_type = read_database_csv("postgresql_investor_type_summary_week10.csv")
    pg_fund_status = read_database_csv("postgresql_fund_enrichment_status_week10.csv")

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    story = [
        p("第十周任务报告：研究型数据集、探索性统计与数据库导入规范化", "title"),
        p(f"姓名：霍泓锟    日期：{RUN_DATE}", "meta"),
        p("一、本周任务定位", "h1"),
        p(
            "第十周承接第九周成果，把8家公司三表数据进一步整理为公司层研究面板，并补充投资主体画像、基金核验队列、描述统计、相关性和探索性OLS。重点不是机械增加文件数量，而是让数据能够支撑后续研究问题。",
            "body",
        ),
        p(
            "本周继续坚持PDF未披露就留空。备案编码、GP和LP结构没有从三表直接披露时，不使用主体名称推断，而是进入后续人工或外部权威来源核验队列。",
            "body",
        ),
        p("二、核心结果", "h1"),
    ]

    investor_count = len(read_csv("investor_profile_week10.csv"))
    postgres_status = (
        "临时库导入查询完成"
        if not pg_summary.empty
        else display_status(postgres.loc[postgres["check_name"].eq("postgres_import"), "status"].iloc[0])
    )
    add_table(
        story,
        ["指标", "数值", "说明"],
        [
            ["样本公司", panel["stock_code"].nunique(), "沿用统一8家公司样本"],
            ["公司层研究面板", len(panel), "一家公司一行"],
            ["投资主体画像", investor_count, "主体名称与类型组合"],
            ["基金补充核验队列", len(fund_queue), "备案编码、GP、LP结构留空待核验"],
            ["探索性OLS模型", len(reg), "仅用于展示研究路径"],
            [
                "PostgreSQL状态",
                postgres_status,
                "55432端口临时实例真实导入；5432主库仍需口令"
                if not pg_summary.empty
                else "需本机口令后真实导入",
            ],
        ],
        [34, 25, 105],
    )

    story.append(p("三、公司层研究变量", "h1"))
    add_table(
        story,
        ["代码", "公司", "板块", "PE/VC占比", "强度指数", "第一大股东", "有效股东数", "质量"],
        panel[
            [
                "stock_code",
                "company_short",
                "market",
                "broad_pevc_record_share",
                "pevc_strength_index",
                "top1_ratio_pct",
                "effective_shareholder_count",
                "quality_gate",
            ]
        ].values.tolist(),
        [18, 22, 16, 20, 20, 20, 20, 18],
    )

    story.append(p("四、板块描述性统计", "h1"))
    add_table(
        story,
        ["板块", "公司数", "平均PE/VC强度", "平均PE/VC占比", "平均第一大股东", "平均有效股东数"],
        board[
            [
                "market",
                "company_count",
                "avg_pevc_strength_index",
                "avg_broad_pevc_record_share",
                "avg_top1_ratio_pct",
                "avg_effective_shareholder_count",
            ]
        ].values.tolist(),
        [22, 18, 32, 32, 32, 32],
    )
    story.append(
        p(
            "每个板块仅2家公司，因此板块均值只能作为研究假设来源。第十周更重要的成果是变量可被自动重算，异常样本有独立标记。",
            "body",
        )
    )

    story.append(p("五、探索性OLS", "h1"))
    add_table(
        story,
        ["样本", "被解释变量", "解释变量", "n", "系数", "R方"],
        reg[
            [
                "sample_scope",
                "dependent_variable",
                "independent_variable",
                "n",
                "coef_x",
                "r_squared",
            ]
        ].head(8).values.tolist(),
        [24, 42, 42, 12, 20, 16],
    )
    story.append(
        p(
            "OLS只用于说明从研究问题到变量和模型的路径。当前样本量太小，且披露口径不完全一致，不能解释为因果关系。",
            "body",
        )
    )

    story.append(p("六、基金补充核验队列", "h1"))
    add_table(
        story,
        ["投资主体", "类型", "优先级", "涉及公司", "披露状态"],
        fund_queue[
            ["investor_name", "investor_type_final", "manual_priority", "companies", "disclosure_status"]
        ].head(8).values.tolist(),
        [58, 20, 34, 24, 48],
    )
    story.append(
        p(
            "基金队列中的备案编码、GP和LP结构仍为空，这是有意保留的披露边界，而不是漏填。后续需回PDF章节或使用基金业协会、工商资料逐条补证。",
            "body",
        )
    )

    story.append(p("七、PostgreSQL结果与数据披露", "h1"))
    if not pg_summary.empty:
        story.append(
            p(
                "本周使用本机PostgreSQL 18工具链启动55432端口临时实例，导入10张结果表并通过SQL导出披露数据。这样可以保留真实数据库执行结果，同时不伪造需要口令的5432主库入库状态。",
                "body",
            )
        )
        add_table(
            story,
            ["披露项目", "披露值", "来源说明"],
            pg_summary[["item", "value", "source_note"]].values.tolist(),
            [32, 36, 98],
        )
        add_table(
            story,
            ["表名", "行数"],
            pg_counts[["table_name", "row_count"]].values.tolist(),
            [110, 25],
        )
        add_table(
            story,
            ["代码", "公司", "板块", "PE/VC占比", "强度指数", "第一大股东", "有效股东数", "质量"],
            pg_company[
                [
                    "stock_code",
                    "company_short",
                    "market",
                    "broad_pevc_record_share",
                    "pevc_strength_index",
                    "top1_ratio_pct",
                    "effective_shareholder_count",
                    "quality_gate",
                ]
            ].values.tolist(),
            [18, 22, 16, 20, 20, 20, 20, 18],
        )
        add_table(
            story,
            ["主体类型", "画像行数", "来源记录数", "公司出现次数", "广义PE/VC主体", "基金/平台主体"],
            pg_investor_type[
                [
                    "investor_type_final",
                    "investor_profile_rows",
                    "source_record_count",
                    "company_mentions",
                    "broad_pevc_profiles",
                    "fund_like_profiles",
                ]
            ].values.tolist(),
            [32, 21, 23, 25, 25, 25],
        )
        add_table(
            story,
            ["优先级", "队列行数", "备案编码已填", "GP已填", "LP已填", "披露状态"],
            pg_fund_status[
                [
                    "manual_priority",
                    "fund_queue_rows",
                    "amac_code_filled",
                    "gp_filled",
                    "lp_structure_filled",
                    "disclosure_status",
                ]
            ].values.tolist(),
            [34, 20, 24, 18, 18, 50],
        )
        story.append(
            p(
                "基金队列中备案编码、GP和LP结构均为0条已填，说明当前三表没有直接披露这些字段；本周选择保留空值边界，后续再用PDF原文、基金业协会或工商资料补证。",
                "body",
            )
        )
    else:
        story.append(
            p(
                "当前尚未运行临时PostgreSQL导入脚本。本节保留数据库脚本和连接审计，运行database/run_postgres_temp_week10.ps1后会生成披露表。",
                "body",
            )
        )

    story.append(p("八、验证与下一步", "h1"))
    validation_display = validation[["check_item", "status", "result", "note"]].copy()
    validation_display["status"] = validation_display["status"].map(display_status)
    add_table(
        story,
        ["检查项", "状态", "结果", "说明"],
        validation_display.values.tolist(),
        [38, 25, 50, 70],
    )
    story.append(
        p(
            "下一周应优先把临时PostgreSQL流程迁移到本人长期数据库并保存行数校验日志，同时扩展样本数量，并对P1基金主体补充备案编码、GP/LP结构和来源证据。",
            "body",
        )
    )

    doc.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    main()
