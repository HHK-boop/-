from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
OUTPUTS = ROOT / "outputs"
VALIDATION = ROOT / "validation"
VALIDATION.mkdir(parents=True, exist_ok=True)


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    summary = json.loads((OUTPUTS / "week13_summary.json").read_text(encoding="utf-8"))
    selected = rows(DERIVED / "week13_selected_companies.csv")
    evidence = rows(DERIVED / "week13_auto_evidence_candidates.csv")
    profiles = rows(DERIVED / "week13_investor_profile.csv")
    review = rows(DERIVED / "week13_manual_review_queue.csv")
    pg_counts = rows(ROOT / "database" / "postgresql_week13_table_counts.csv")
    workbook = OUTPUTS / "霍泓锟_第十三周扩样核验结果.xlsx"
    report = ROOT / "report" / "霍泓锟_第十三周扩样抽取与人工核验报告.docx"

    checks: list[dict[str, str]] = []

    def check(name: str, condition: bool, actual, expected: str) -> None:
        checks.append({
            "check_item": name,
            "status": "PASS" if condition else "FAIL",
            "actual": str(actual),
            "expected": expected,
        })

    check("12家公司齐全", len(selected) == 12, len(selected), "12")
    source_paths = [ROOT / row["package_text_file"] for row in selected]
    check("12份源文本存在", all(path.exists() and path.stat().st_size > 0 for path in source_paths), sum(path.exists() for path in source_paths), "12")
    check("页码总数", sum(int(row["page_count"]) for row in selected) == 2160, sum(int(row["page_count"]) for row in selected), "2160")
    check("Auto候选记录", len(evidence) == int(summary["auto_candidate_record_count"]), len(evidence), str(summary["auto_candidate_record_count"]))
    retained = sum(row["auto_status"].startswith("保留") for row in evidence)
    excluded = sum(row["auto_status"].startswith("排除") for row in evidence)
    check("保留候选记录", retained == int(summary["retained_candidate_record_count"]), retained, str(summary["retained_candidate_record_count"]))
    check("排除误命中记录", excluded == int(summary["excluded_transfer_boilerplate_count"]), excluded, str(summary["excluded_transfer_boilerplate_count"]))
    check("去重主体候选", len(profiles) == int(summary["unique_investor_candidate_count"]), len(profiles), str(summary["unique_investor_candidate_count"]))
    deep_fields_blank = all(not row.get("amac_filing_code") and not row.get("gp_name") and not row.get("lp_structure") for row in profiles)
    check("未披露深度字段留空", deep_fields_blank, deep_fields_blank, "True")
    check("人工复核队列", len(review) == int(summary["manual_review_queue_count"]) and len(review) >= retained * 0.10, len(review), ">=10% retained candidates")
    check("PostgreSQL 11表", len(pg_counts) == 11, len(pg_counts), "11")
    check("PostgreSQL 492行", sum(int(row["row_count"]) for row in pg_counts) == 492, sum(int(row["row_count"]) for row in pg_counts), "492")
    check("Excel已生成", workbook.exists() and workbook.stat().st_size > 0, workbook.stat().st_size if workbook.exists() else 0, ">0 bytes")
    sheet_count = 0
    if workbook.exists():
        with zipfile.ZipFile(workbook) as archive:
            sheet_count = sum(name.startswith("xl/worksheets/sheet") and name.endswith(".xml") for name in archive.namelist())
    check("Excel工作表数量", sheet_count == 14, sheet_count, "14")
    inspect_text = (Path(str(workbook) + ".inspect.ndjson").read_text(encoding="utf-8") if Path(str(workbook) + ".inspect.ndjson").exists() else "")
    error_tokens = ["#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A", "#NUM!", "#NULL!", "#SPILL!", "#CALC!"]
    check("Excel公式错误扫描", not any(token in inspect_text for token in error_tokens), "clean" if not any(token in inspect_text for token in error_tokens) else "error", "clean")
    check("Word报告已生成", report.exists() and report.stat().st_size > 0, report.stat().st_size if report.exists() else 0, ">0 bytes")

    output = VALIDATION / "week13_submission_validation.csv"
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check_item", "status", "actual", "expected"])
        writer.writeheader()
        writer.writerows(checks)

    failed = [row for row in checks if row["status"] != "PASS"]
    print(json.dumps({"checks": len(checks), "passed": len(checks) - len(failed), "failed": failed}, ensure_ascii=False, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
