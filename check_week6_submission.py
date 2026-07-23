"""Lightweight checks before submitting the Week 6 package."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


REQUIRED_CODES = {"603418", "001282", "301581", "301563", "688758", "688775", "920100", "920116"}
FORBIDDEN_CODES = {"603072", "920091"}
REQUIRED_DIRS = [
    "data",
    "pipeline",
    "prompts",
    "manual_gold",
    "auto_output",
    "final",
    "validation",
    "review",
    "report",
    "logs",
]
REQUIRED_FILES = [
    "README.md",
    "requirements.txt",
    "data/manifest/company_manifest.csv",
    "pipeline/run_all.py",
    "pipeline/run_week6_pipeline.py",
    "auto_output/subscription_auto.csv",
    "auto_output/transfer_auto.csv",
    "auto_output/equity_snapshot_auto.csv",
    "manual_gold/subscription_gold.csv",
    "manual_gold/transfer_gold.csv",
    "manual_gold/equity_snapshot_gold.csv",
    "final/subscription_final.csv",
    "final/transfer_final.csv",
    "final/equity_snapshot_final.csv",
    "validation/schema_result.csv",
    "validation/cross_check.csv",
    "validation/auto_vs_gold.csv",
    "review/intra_group_review.csv",
    "report/week6_report.md",
    "logs/run_log.csv",
]


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def check(root: Path) -> list[str]:
    issues: list[str] = []
    for rel in REQUIRED_DIRS:
        if not (root / rel).is_dir():
            issues.append(f"missing directory: {rel}")
    for rel in REQUIRED_FILES:
        if not (root / rel).is_file():
            issues.append(f"missing file: {rel}")

    manifest_path = root / "data" / "manifest" / "company_manifest.csv"
    if manifest_path.exists():
        manifest_codes = {r.get("stock_code", "") for r in rows(manifest_path)}
        missing = REQUIRED_CODES - manifest_codes
        forbidden = FORBIDDEN_CODES & manifest_codes
        if missing:
            issues.append(f"manifest missing required codes: {sorted(missing)}")
        if forbidden:
            issues.append(f"manifest includes forbidden substitute codes: {sorted(forbidden)}")

    for rel in [
        "auto_output/subscription_auto.csv",
        "auto_output/transfer_auto.csv",
        "auto_output/equity_snapshot_auto.csv",
        "final/subscription_final.csv",
        "final/transfer_final.csv",
        "final/equity_snapshot_final.csv",
    ]:
        path = root / rel
        if path.exists() and len(rows(path)) == 0:
            issues.append(f"empty table: {rel}")

    transfer_final = root / "final" / "transfer_final.csv"
    if transfer_final.exists() and len(rows(transfer_final)) < 4:
        issues.append("final/transfer_final.csv has fewer than 4 confirmed transfer records")

    run_log = root / "logs" / "run_log.csv"
    if run_log.exists():
        notes = " ".join(r.get("note", "") for r in rows(run_log))
        if "manual_gold/final are not read before Auto generation" not in notes:
            issues.append("run_log does not document Auto independence from manual_gold/final")

    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Week 6 submission completeness.")
    parser.add_argument("--root", default=".", help="Repository root.")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    issues = check(root)
    if issues:
        print("Submission check failed:")
        for issue in issues:
            print(f"- {issue}")
        raise SystemExit(1)
    print("Submission check passed.")


if __name__ == "__main__":
    main()
