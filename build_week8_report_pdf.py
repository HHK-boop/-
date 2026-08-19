"""Build the Week 8 report PDF from pipeline outputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
REVIEW = ROOT / "review"
OUTPUTS = ROOT / "outputs"
REPORT = ROOT / "report"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def register_fonts() -> tuple[str, str]:
    candidates = [
        ("CJK", r"C:\Windows\Fonts\msyh.ttc"),
        ("CJK", r"C:\Windows\Fonts\simsun.ttc"),
        ("CJK", r"C:\Windows\Fonts\simhei.ttf"),
        ("CJK", r"C:\Windows\Fonts\Deng.ttf"),
    ]
    for name, path in candidates:
        if Path(path).exists():
            pdfmetrics.registerFont(TTFont(name, path))
            return name, name
    return "Helvetica", "Helvetica-Bold"


FONT, FONT_BOLD = register_fonts()


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="CNTitle",
        parent=styles["Title"],
        fontName=FONT_BOLD,
        fontSize=20,
        leading=28,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#17365D"),
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        name="CNHeading",
        parent=styles["Heading2"],
        fontName=FONT_BOLD,
        fontSize=13,
        leading=18,
        textColor=colors.HexColor("#17365D"),
        spaceBefore=8,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="CNBody",
        parent=styles["BodyText"],
        fontName=FONT,
        fontSize=9.6,
        leading=15,
        alignment=TA_LEFT,
        spaceAfter=5,
    )
)
styles.add(
    ParagraphStyle(
        name="CNCell",
        parent=styles["BodyText"],
        fontName=FONT,
        fontSize=7.4,
        leading=10,
        alignment=TA_LEFT,
    )
)


HEADER_LABELS = {
    "week8_task": "本周任务",
    "status": "状态",
    "evidence_file": "证据文件",
    "remaining_work": "剩余工作",
    "stock_code": "代码",
    "company_short": "公司",
    "market": "板块",
    "subscription_records": "认缴记录",
    "snapshot_records": "快照记录",
    "transfer_records": "转让记录",
    "total_records": "总记录",
    "broad_pevc_records": "广义PE/VC记录",
    "evidence_coverage": "证据覆盖率",
    "table_name": "表名",
    "pdf_page_coverage": "页码覆盖率",
    "investor_type_coverage": "分类覆盖率",
    "review_queue_items": "复核项",
    "quality_note": "说明",
    "investor_type_final": "主体类型",
    "record_count": "记录数",
    "share": "占比",
    "field": "字段",
    "records": "记录数",
    "missing_count": "缺失数",
    "missing_rate": "缺失率",
    "week8_principle": "处理原则",
    "queue_id": "编号",
    "issue_type": "问题类型",
    "detail": "说明",
    "company_count": "公司数",
    "broad_pevc_record_share": "广义PE/VC占比",
    "has_vc_or_pe": "是否VC/PE",
    "vc_record_count": "VC记录",
    "pe_record_count": "PE记录",
    "p1_review_item_count": "P1复核项",
}


def p(text: str, style: str = "CNBody") -> Paragraph:
    return Paragraph(str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), styles[style])


def table_from_records(records: list[dict[str, str]], headers: list[str], widths: list[float]) -> Table:
    data = [[p(HEADER_LABELS.get(h, h), "CNCell") for h in headers]]
    for row in records:
        data.append([p(row.get(h, ""), "CNCell") for h in headers])
    tbl = Table(data, colWidths=widths, repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAF7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17365D")),
                ("FONTNAME", (0, 0), (-1, -1), FONT),
                ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B7C9D6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return tbl


def story() -> list:
    summary = json.loads((OUTPUTS / "week8_summary.json").read_text(encoding="utf-8"))
    company_summary = read_csv(DERIVED / "company_summary_week8.csv")
    quality_metrics = read_csv(DERIVED / "quality_metrics_week8.csv")
    investor_stats = read_csv(DERIVED / "investor_type_stats_week8.csv")
    missing_top = read_csv(DERIVED / "field_missing_summary_week8.csv")[:10]
    board_stats = read_csv(DERIVED / "board_stats_week8.csv")
    research_vars = read_csv(DERIVED / "research_variables_week8.csv")
    review_queue = read_csv(REVIEW / "week8_review_queue.csv")
    task_status = read_csv(DERIVED / "week8_task_status.csv")

    out = []
    out.append(p("第八周任务报告：PE/VC招股书三表质量审计与研究分析准备", "CNTitle"))
    out.append(p("姓名：霍泓锟　主题：第七周三表数据的可审计化、数据库化和描述性统计准备"))
    out.append(Spacer(1, 4))

    out.append(p("一、本周任务定位", "CNHeading"))
    out.append(
        p(
            "本周承接此前提出的未来计划，目标是把第七周形成的8家公司三表Final数据，从“可以提交的抽取结果”进一步推进为“可以复核、可以入库、可以用于初步研究分析”的数据包。"
            "因此，本周不是简单增加文件数量，而是围绕四件事展开：数据质量审计、投资主体分类统计、人工复核队列整理、PostgreSQL和研究变量准备。"
        )
    )
    out.append(
        p(
            f"主流程运行后共读取认缴/增资记录 {summary['subscription_records']} 条、股权快照记录 {summary['snapshot_records']} 条、股权转让记录 {summary['transfer_records']} 条，"
            f"合计覆盖8家公司，并识别出广义PE/VC相关记录 {summary['broad_pevc_records']} 条。"
        )
    )

    out.append(p("二、本周任务完成情况", "CNHeading"))
    out.append(
        table_from_records(
            task_status,
            ["week8_task", "status", "evidence_file", "remaining_work"],
            [42 * mm, 28 * mm, 48 * mm, 55 * mm],
        )
    )

    out.append(p("三、样本公司和记录规模", "CNHeading"))
    out.append(
        p(
            "本周继续使用统一8家公司样本，没有再用早期不一致公司替代。脚本在读入时按公司简称修正证券代码，避免001282被表格软件转成1282。"
        )
    )
    out.append(
        table_from_records(
            company_summary,
            [
                "stock_code",
                "company_short",
                "market",
                "subscription_records",
                "snapshot_records",
                "transfer_records",
                "broad_pevc_records",
                "evidence_coverage",
            ],
            [18 * mm, 18 * mm, 17 * mm, 22 * mm, 22 * mm, 20 * mm, 22 * mm, 22 * mm],
        )
    )

    out.append(p("四、质量审计结果", "CNHeading"))
    out.append(
        p(
            "质量审计分为三层：第一层检查页码和证据覆盖率；第二层检查investor_type分类覆盖率；第三层把比例合计异常、单价反推异常和转让证据不足写入review队列。"
            "本周坚持“PDF未披露就留空”的原则，缺失值不被替换为0。"
        )
    )
    out.append(
        table_from_records(
            quality_metrics,
            [
                "table_name",
                "total_records",
                "pdf_page_coverage",
                "evidence_coverage",
                "investor_type_coverage",
                "review_queue_items",
                "quality_note",
            ],
            [25 * mm, 20 * mm, 22 * mm, 23 * mm, 24 * mm, 22 * mm, 38 * mm],
        )
    )
    out.append(
        p(
            "需要说明的是，赛分科技的比例异常在第七周遗留日志和第八周自动脚本中均被命中，属于同一根因的重复提示，不应理解为两个互相独立的问题。"
        )
    )

    out.append(p("五、investor_type 分类与描述性统计", "CNHeading"))
    out.append(
        p(
            "第八周继续把investor_type作为核心字段。原因是招股书三表覆盖全部股东，不等同于纯PE/VC事件表；如果不先分类，自然人、员工持股平台、实际控制人和外部基金会被混在一起，后续研究解释会失真。"
        )
    )
    out.append(table_from_records(investor_stats, ["investor_type_final", "record_count", "share"], [65 * mm, 35 * mm, 35 * mm]))
    out.append(
        p(
            "从统计看，自然人仍是最大类别，说明三表首先反映的是股权结构全貌；VC、PE、政府基金、产业资本/CVC等类别才是后续PE/VC研究需要重点提取的子样本。"
        )
    )

    out.append(p("六、字段缺失和人工复核队列", "CNHeading"))
    out.append(
        p(
            "字段缺失主要集中在价格、股份数量和部分时点比例上。这里的缺失不能简单理解为抽取失败，很多时候是PDF原文确实没有披露。第八周把这类情况区分为INFO和P1人工复核。"
        )
    )
    out.append(
        table_from_records(
            missing_top,
            ["table_name", "field", "records", "missing_count", "missing_rate", "week8_principle"],
            [28 * mm, 42 * mm, 18 * mm, 22 * mm, 20 * mm, 42 * mm],
        )
    )
    out.append(Spacer(1, 5))
    out.append(
        table_from_records(
            review_queue[:10],
            ["queue_id", "stock_code", "company_short", "issue_type", "status", "detail"],
            [22 * mm, 20 * mm, 24 * mm, 30 * mm, 25 * mm, 55 * mm],
        )
    )

    out.append(PageBreak())
    out.append(p("七、板块统计和研究变量草案", "CNHeading"))
    out.append(
        p(
            "为了衔接后续一个月计划，本周新增公司层面研究变量草案，包括是否存在VC/PE、VC记录数、PE记录数、广义PE/VC记录占比、自然人记录占比、转让事件数量和P1复核项数量。"
        )
    )
    out.append(
        table_from_records(
            board_stats,
            [
                "market",
                "company_count",
                "subscription_records",
                "snapshot_records",
                "transfer_records",
                "broad_pevc_records",
                "broad_pevc_record_share",
            ],
            [24 * mm, 22 * mm, 26 * mm, 26 * mm, 24 * mm, 26 * mm, 28 * mm],
        )
    )
    out.append(Spacer(1, 5))
    out.append(
        table_from_records(
            research_vars,
            [
                "stock_code",
                "company_short",
                "market",
                "has_vc_or_pe",
                "vc_record_count",
                "pe_record_count",
                "broad_pevc_record_share",
                "p1_review_item_count",
            ],
            [18 * mm, 20 * mm, 18 * mm, 22 * mm, 22 * mm, 22 * mm, 28 * mm, 25 * mm],
        )
    )

    out.append(p("八、数据库化准备", "CNHeading"))
    out.append(
        p(
            "本周在第七周schema基础上新增四张派生表：公司汇总表、质量指标表、人工复核队列表和研究变量表，并提供`database/import_week8_derived_tables.sql`。"
            "这些表不替代原始三表，而是作为分析层和检查层，便于后续在PostgreSQL中按公司、板块、投资主体类型和问题状态查询。"
        )
    )
    out.append(
        p(
            "数据库设计仍遵守三个原则：证券代码保存为文本；PDF页码保存为文本；未披露数值保存为NULL而不是0。这样可以避免后续统计时把披露缺失误解为真实数值。"
        )
    )

    out.append(p("九、本周不足与第九周计划", "CNHeading"))
    out.append(
        p(
            "本周不足主要有三点。第一，复杂基金主体仍需要基金备案编码、GP/LP结构和工商信息进一步确认，当前分类仍有规则判断成分。第二，黄山谷捷和赛分科技的比例异常还没有逐页截图证明，需要下一周回PDF核验。第三，目前只有8家公司，适合做流程验证和描述性统计，不适合直接做正式回归。"
        )
    )
    out.append(
        p(
            "第九周建议优先完成三项工作：逐条处理P1复核队列；真实导入PostgreSQL并记录导入日志；在研究变量草案基础上提出一个小型问题，例如“不同板块PE/VC进入强度是否不同”或“有VC/PE参与的公司上市前股权结构是否更分散”。"
        )
    )

    return out


def write_markdown_shadow() -> None:
    summary = json.loads((OUTPUTS / "week8_summary.json").read_text(encoding="utf-8"))
    task_status = read_csv(DERIVED / "week8_task_status.csv")
    company_summary = read_csv(DERIVED / "company_summary_week8.csv")
    review_queue = read_csv(REVIEW / "week8_review_queue.csv")
    lines = [
        "# 第八周任务报告：PE/VC招股书三表质量审计与研究分析准备",
        "",
        "姓名：霍泓锟",
        "",
        "## 核心结果",
        "",
        f"- 认缴/增资记录：{summary['subscription_records']}条",
        f"- 股权快照记录：{summary['snapshot_records']}条",
        f"- 股权转让记录：{summary['transfer_records']}条",
        f"- 广义PE/VC相关记录：{summary['broad_pevc_records']}条",
        f"- P1人工复核项：{summary['p1_review_items']}条",
        "",
        "## 本周任务状态",
        "",
        "|任务|状态|证据文件|剩余工作|",
        "|---|---|---|---|",
    ]
    for row in task_status:
        lines.append(
            f"|{row['week8_task']}|{row['status']}|{row['evidence_file']}|{row['remaining_work']}|"
        )
    lines += [
        "",
        "## 公司处理情况",
        "",
        "|代码|公司|板块|认缴|快照|转让|广义PE/VC记录|证据覆盖率|",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in company_summary:
        lines.append(
            f"|{row['stock_code']}|{row['company_short']}|{row['market']}|{row['subscription_records']}|{row['snapshot_records']}|{row['transfer_records']}|{row['broad_pevc_records']}|{row['evidence_coverage']}%|"
        )
    lines += [
        "",
        "## 人工复核队列",
        "",
        "|编号|公司|问题|状态|说明|",
        "|---|---|---|---|---|",
    ]
    for row in review_queue:
        lines.append(
            f"|{row['queue_id']}|{row['company_short']}|{row['issue_type']}|{row['status']}|{row['detail']}|"
        )
    (REPORT / "week8_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT, 8)
    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.drawRightString(200 * mm, 10 * mm, f"第 {doc.page} 页")
    canvas.restoreState()


def main() -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    write_markdown_shadow()
    pdf_path = REPORT / "霍泓锟_第八周任务报告.pdf"
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    doc.build(story(), onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(f"saved {pdf_path}")


if __name__ == "__main__":
    main()
