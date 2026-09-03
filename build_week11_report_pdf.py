"""Build a PDF version of the Week 11 report."""

from __future__ import annotations

import csv
from pathlib import Path

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
OUTPUT = REPORT / "霍泓锟_第十一周任务报告.pdf"
RUN_DATE = "2026年9月2日"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def register_font() -> str:
    for font in (Path(r"C:\Windows\Fonts\msyh.ttc"), Path(r"C:\Windows\Fonts\simsun.ttc"), Path(r"C:\Windows\Fonts\simhei.ttf")):
        if font.exists():
            pdfmetrics.registerFont(TTFont("CNFont", str(font)))
            return "CNFont"
    return "Helvetica"


FONT = register_font()
BASE = getSampleStyleSheet()
S = {
    "title": ParagraphStyle("title", parent=BASE["Title"], fontName=FONT, fontSize=18, leading=24, textColor=colors.HexColor("#17365D"), alignment=TA_CENTER, spaceAfter=8),
    "meta": ParagraphStyle("meta", parent=BASE["Normal"], fontName=FONT, fontSize=10, leading=14, alignment=TA_CENTER, spaceAfter=12),
    "h1": ParagraphStyle("h1", parent=BASE["Heading1"], fontName=FONT, fontSize=13, leading=17, textColor=colors.HexColor("#1F4D78"), spaceBefore=8, spaceAfter=6),
    "body": ParagraphStyle("body", parent=BASE["Normal"], fontName=FONT, fontSize=9.2, leading=14, alignment=TA_LEFT, spaceAfter=6),
    "cell": ParagraphStyle("cell", parent=BASE["Normal"], fontName=FONT, fontSize=6.8, leading=9.2, alignment=TA_LEFT),
}


def p(text: object, style: str = "cell") -> Paragraph:
    return Paragraph("" if text is None else str(text), S[style])


def add_table(story, headers: list[str], rows: list[list[object]], widths: list[float]) -> None:
    data = [[p(h) for h in headers]]
    data.extend([[p(value) for value in row] for row in rows])
    table = Table(data, colWidths=[w * mm for w in widths], repeatRows=1, splitByRow=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAF7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17365D")),
                ("FONTNAME", (0, 0), (-1, -1), FONT),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D0D7DE")),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 6))


def main() -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    quality = read_csv(DERIVED / "week11_quality_dashboard.csv")
    db_plan = read_csv(DERIVED / "week11_database_migration_plan.csv")
    fund_queue = read_csv(DERIVED / "week11_fund_deep_enrichment_queue.csv")
    manual = read_csv(DERIVED / "week11_manual_verification_template.csv")
    research = read_csv(DERIVED / "week11_research_design_matrix.csv")
    expansion = read_csv(DERIVED / "week11_sample_expansion_plan.csv")
    pg_disclosure = read_csv(DATABASE / "postgresql_week11_disclosure.csv")
    completion = read_csv(DERIVED / "week11_completion_checklist.csv")

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="霍泓锟 第十一周任务报告",
    )
    story = [
        p("霍泓锟 第十一周任务报告", "title"),
        p(f"数据库长期化迁移准备与基金深度字段核验 | 提交日期：{RUN_DATE}", "meta"),
        p("本周承接第十周研究面板和PostgreSQL结果，将重点转向长期库迁移、基金备案编码/GP/LP核验队列、以及下一阶段研究设计。未在PDF或外部来源明确披露的字段继续留空，不由名称推断。", "body"),
        p("一、本周核心结果", "h1"),
    ]
    add_table(story, ["指标", "数值", "解释"], [[r.get("metric", ""), r.get("value", ""), r.get("interpretation", "")] for r in quality], [36, 22, 118])

    story.append(p("二、PostgreSQL迁移与披露", "h1"))
    story.append(p("本周同时保留临时库复现脚本和长期库迁移脚本。临时库验证CSV和SQL可导入；长期库需要主库口令，不能把无密码状态误报为成功。", "body"))
    add_table(story, ["任务", "状态", "证据", "下一步"], [[r.get("task", ""), r.get("status", ""), r.get("evidence", ""), r.get("next_action", "")] for r in db_plan], [30, 26, 72, 48])
    if pg_disclosure:
        add_table(story, ["项目", "值", "说明"], [[r.get("item", ""), r.get("value", ""), r.get("source_note", "")] for r in pg_disclosure], [42, 28, 106])

    story.append(p("三、基金深度字段核验", "h1"))
    story.append(p(f"本周基金深度队列共{len(fund_queue)}条，人工核验事项共{len(manual)}条。字段范围包括备案编码、GP和LP结构，先按P1优先级回PDF页码核验，再决定是否使用基金业协会或工商来源补充。", "body"))
    add_table(
        story,
        ["ID", "公司", "投资主体", "类型", "页码", "原则"],
        [[r.get("record_id", ""), r.get("company_short", ""), r.get("investor_name", ""), r.get("investor_type_final", ""), r.get("pdf_pages_observed", ""), r.get("engineering_rule", "")] for r in fund_queue[:10]],
        [14, 20, 62, 18, 24, 38],
    )

    story.append(p("四、研究设计与扩样计划", "h1"))
    add_table(story, ["研究问题", "核心变量", "方法", "当前限制"], [[r.get("research_question", ""), r.get("key_explanatory_variable", ""), r.get("method", ""), r.get("current_limit", "")] for r in research], [58, 42, 32, 44])
    add_table(story, ["周期", "范围", "目标", "验收标准", "状态"], [[r.get("period", ""), r.get("scope", ""), r.get("target", ""), r.get("success_criteria", ""), r.get("status", "")] for r in expansion], [22, 30, 58, 48, 18])

    story.append(p("五、可复现提交说明", "h1"))
    story.append(p("统一入口为 code/run_all_week11_codex.ps1。运行后依次生成派生表、临时PostgreSQL披露结果、Excel工作簿、Word报告和PDF报告。长期库导入脚本单独保留在 database/run_postgres_persistent_week11.ps1。", "body"))
    add_table(story, ["项目", "状态", "证据"], [[r.get("item", ""), r.get("status", ""), r.get("evidence", "")] for r in completion], [54, 24, 98])

    story.append(p("六、不足与第十二周任务", "h1"))
    story.append(p("当前不足主要有三点：本机5432长期库缺少口令，基金AMAC/GP/LP字段还没有外部核验，8家公司样本量不足以支撑稳健计量结论。第十二周应优先完成PGPASSWORD配置、P1基金主体核验，以及四个板块的新增样本扩展。", "body"))

    doc.build(story)
    print(f"saved {OUTPUT}")


if __name__ == "__main__":
    main()
