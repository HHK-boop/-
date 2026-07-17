from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
REQUIRED_FILES = [
    ROOT / "config" / "sample_manifest.csv",
    ROOT / "config" / "investor_type_taxonomy.csv",
    ROOT / "config" / "schema_config.json",
    ROOT / "data" / "manual_gold" / "eight_company_manual_gold.csv",
    ROOT / "code" / "eight_company_pipeline.py",
    ROOT / "run_pipeline.py",
    OUTPUTS / "pdf_inventory.csv",
    OUTPUTS / "toc_keyword_positioning.csv",
    OUTPUTS / "gold_standard.csv",
    OUTPUTS / "gold_standard.jsonl",
    OUTPUTS / "auto_output_candidates.csv",
    OUTPUTS / "comparison_auto_vs_manual.csv",
    OUTPUTS / "accuracy_metrics.csv",
    OUTPUTS / "gold_standard_report.md",
    OUTPUTS / "accuracy_report.md",
    OUTPUTS / "markdown_tables" / "gold_standard_all.md",
    OUTPUTS / "markdown_tables" / "markdown_table_extraction_report.md",
]


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []

    pdfs = list((ROOT / "data" / "raw_pdfs").glob("*.pdf"))
    if len(pdfs) != 8:
        fail(f"expected 8 raw PDFs, got {len(pdfs)}", errors)
    for pdf in pdfs:
        if pdf.stat().st_size < 1024 * 100:
            fail(f"PDF too small: {pdf.name}", errors)

    for path in REQUIRED_FILES:
        if not path.exists():
            fail(f"missing file: {path}", errors)
        elif path.stat().st_size == 0:
            fail(f"empty file: {path}", errors)

    if (OUTPUTS / "gold_standard.csv").exists():
        gold = read_csv(OUTPUTS / "gold_standard.csv")
        sample_ids = {row["sample_id"] for row in gold}
        if sample_ids != {"MB001", "MB002", "GEM001", "GEM002", "STAR001", "STAR002", "BSE001", "BSE002"}:
            fail(f"gold sample ids mismatch: {sample_ids}", errors)
        if len(gold) < 55:
            fail(f"gold should contain at least 55 records, got {len(gold)}", errors)
        if not any(row["investor_type"] == "员工持股平台" for row in gold):
            fail("gold must include employee-platform exclusion examples", errors)
        if not any(row["blank_reason"] for row in gold):
            fail("gold must include blank_reason examples for PDF-undisclosed fields", errors)
        if not any(row["pe_fund_filing_code"] for row in gold):
            fail("gold must include disclosed PE fund filing codes", errors)

    if (OUTPUTS / "accuracy_metrics.csv").exists():
        metrics = {row["metric"]: row for row in read_csv(OUTPUTS / "accuracy_metrics.csv")}
        for metric in [
            "investor_type_accuracy",
            "filing_code_accuracy_when_pdf_disclosed",
            "gp_name_accuracy_when_pdf_disclosed",
        ]:
            if metric not in metrics:
                fail(f"missing metric: {metric}", errors)

    if (OUTPUTS / "gold_standard.jsonl").exists():
        with (OUTPUTS / "gold_standard.jsonl").open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                try:
                    json.loads(line)
                except json.JSONDecodeError as exc:
                    fail(f"invalid jsonl line {line_no}: {exc}", errors)

    if errors:
        print("SUBMISSION CHECK FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print("SUBMISSION CHECK PASSED")
    print("Eight-company positioning, gold standard, Markdown tables and accuracy files are complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
