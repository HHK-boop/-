from __future__ import annotations

import csv
import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
REQUIRED_FILES = [
    ROOT / "data" / "raw" / "kangnong_prospectus.pdf",
    ROOT / "data" / "manual_gold" / "kangnong_manual_gold.csv",
    ROOT / "code" / "kangnong_pipeline.py",
    ROOT / "run_pipeline.py",
    OUTPUT_DIR / "manual_gold.csv",
    OUTPUT_DIR / "manual_gold.jsonl",
    OUTPUT_DIR / "auto_output_candidates.csv",
    OUTPUT_DIR / "auto_output_candidates.jsonl",
    OUTPUT_DIR / "comparison_auto_vs_manual.csv",
    OUTPUT_DIR / "validation_report.md",
    OUTPUT_DIR / "evidence_index.csv",
    OUTPUT_DIR / "teacher_discussion_questions.md",
]


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def assert_true(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []

    for file_path in REQUIRED_FILES:
        assert_true(file_path.exists(), f"missing file: {file_path}", errors)
        if file_path.exists():
            assert_true(file_path.stat().st_size > 0, f"empty file: {file_path}", errors)

    if (OUTPUT_DIR / "manual_gold.csv").exists():
        manual = read_csv(OUTPUT_DIR / "manual_gold.csv")
        assert_true(len(manual) == 4, "manual_gold should contain 4 records", errors)
        statuses = {row.get("gold_status", "") for row in manual}
        assert_true({"keep", "exclude"}.issubset(statuses), "manual_gold should include keep and exclude records", errors)
        assert_true(all(row.get("source_pages") for row in manual), "manual_gold records must have source_pages", errors)

    if (OUTPUT_DIR / "auto_output_candidates.csv").exists():
        auto = read_csv(OUTPUT_DIR / "auto_output_candidates.csv")
        assert_true(len(auto) >= 4, "auto_output should contain at least 4 candidate records", errors)
        assert_true(
            any(row.get("candidate_status") == "false_positive_exclude" for row in auto),
            "auto_output should keep a false-positive example",
            errors,
        )

    if (OUTPUT_DIR / "comparison_auto_vs_manual.csv").exists():
        comparison = read_csv(OUTPUT_DIR / "comparison_auto_vs_manual.csv")
        assert_true(len(comparison) == 4, "comparison should contain 4 records", errors)
        assert_true(
            any(row.get("match_level") == "matched_false_positive" for row in comparison),
            "comparison should flag matched_false_positive",
            errors,
        )

    if (OUTPUT_DIR / "evidence_index.csv").exists():
        evidence = read_csv(OUTPUT_DIR / "evidence_index.csv")
        assert_true(len(evidence) >= 6, "evidence_index should contain key PDF pages", errors)
        assert_true(
            all(row.get("screenshot_exists") == "True" for row in evidence),
            "all evidence screenshots should exist",
            errors,
        )

    if (OUTPUT_DIR / "validation_report.md").exists():
        text = (OUTPUT_DIR / "validation_report.md").read_text(encoding="utf-8")
        assert_true(text.count("PASS") >= 4, "validation_report should contain at least 4 PASS checks", errors)

    if (OUTPUT_DIR / "auto_output_candidates.jsonl").exists():
        with (OUTPUT_DIR / "auto_output_candidates.jsonl").open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                try:
                    json.loads(line)
                except json.JSONDecodeError as exc:
                    errors.append(f"invalid jsonl at line {line_no}: {exc}")

    if errors:
        print("SUBMISSION CHECK FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print("SUBMISSION CHECK PASSED")
    print("manual_gold, auto_output, comparison, validation and evidence files are complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
