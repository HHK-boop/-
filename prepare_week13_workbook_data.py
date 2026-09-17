"""Prepare compact typed JSON for the Week 13 workbook builder."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
DATABASE = ROOT / "database"
VALIDATION = ROOT / "validation"
OUTPUTS = ROOT / "outputs"


def read_csv(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def number(value: object) -> object:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return float(text) if "." in text else int(text)
    except ValueError:
        return value


def convert(rows: list[dict[str, object]], numeric_columns: set[str]) -> list[dict[str, object]]:
    converted: list[dict[str, object]] = []
    for row in rows:
        item = dict(row)
        for column in numeric_columns:
            if column in item:
                item[column] = number(item[column])
        converted.append(item)
    return converted


def preview_rows(rows: list[dict[str, object]], source_field: str, target_field: str) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for row in rows:
        item = dict(row)
        text = str(item.get(source_field, ""))
        item[target_field] = text if len(text) <= 180 else text[:177] + "..."
        output.append(item)
    return output


def main() -> None:
    summary_path = OUTPUTS / "week13_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}

    tables = {
        "selected_companies": convert(read_csv(DERIVED / "week13_selected_companies.csv"), {"batch_order", "page_count", "week12_keyword_hits"}),
        "chapter_locator": convert(read_csv(DERIVED / "week13_chapter_locator.csv"), {"first_page", "hit_pages_count"}),
        "auto_evidence": preview_rows(convert(read_csv(DERIVED / "week13_auto_evidence_candidates.csv"), {"source_page", "term_hit_count", "investor_candidate_count"}), "evidence_excerpt", "evidence_preview"),
        "investor_profile": convert(read_csv(DERIVED / "week13_investor_profile.csv"), {"occurrence_count"}),
        "investor_type_rules": read_csv(DERIVED / "week13_investor_type_rules.csv"),
        "event_summary": convert(read_csv(DERIVED / "week13_event_summary.csv"), {"candidate_records", "companies_covered", "high_confidence_records", "with_date", "with_amount_or_shares"}),
        "crosscheck": convert(read_csv(DERIVED / "week13_old_new_crosscheck.csv"), {"old_candidate_record_count", "old_unique_pages", "week13_retained_records", "week13_unique_pages", "overlap_pages", "old_page_recovery_rate", "newly_located_pages"}),
        "company_progress": convert(read_csv(DERIVED / "week13_company_progress.csv"), {"page_count", "chapter_groups_located", "retained_auto_candidates", "excluded_transfer_boilerplate", "investor_name_candidates", "high_confidence_candidates"}),
        "manual_review": preview_rows(convert(read_csv(DERIVED / "week13_manual_review_queue.csv"), {"source_page"}), "evidence_excerpt", "evidence_preview"),
        "weekly_plan": read_csv(DERIVED / "week13_weekly_plan.csv"),
        "validation": read_csv(VALIDATION / "week13_validation_summary.csv"),
        "pg_disclosure": read_csv(DATABASE / "postgresql_week13_disclosure.csv"),
        "pg_table_counts": convert(read_csv(DATABASE / "postgresql_week13_table_counts.csv"), {"row_count"}),
        "pg_event_counts": convert(read_csv(DATABASE / "postgresql_week13_event_counts.csv"), {"candidate_records", "companies_covered", "high_confidence_records"}),
    }
    output = {"summary": summary, "tables": tables}
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    (OUTPUTS / "week13_workbook_data.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved {OUTPUTS / 'week13_workbook_data.json'}")


if __name__ == "__main__":
    main()
