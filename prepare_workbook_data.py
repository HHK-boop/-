"""Prepare JSON input for the spreadsheet renderer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    return df.to_dict("records")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare workbook_data.json from Week 6 CSV outputs.")
    parser.add_argument("--root", default=".", help="Repository root.")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    out_dir = root / "tmp_workbook"
    out_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "summary": read_csv(root / "data" / "manifest" / "company_manifest.csv"),
        "subscription_final": read_csv(root / "final" / "subscription_final.csv"),
        "transfer_final": read_csv(root / "final" / "transfer_final.csv"),
        "equity_snapshot_final": read_csv(root / "final" / "equity_snapshot_final.csv"),
        "cross_check": read_csv(root / "validation" / "cross_check.csv"),
        "auto_vs_gold": read_csv(root / "validation" / "auto_vs_gold.csv"),
        "review": read_csv(root / "review" / "intra_group_review.csv"),
    }
    (out_dir / "workbook_data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Prepared workbook data: {out_dir / 'workbook_data.json'}")


if __name__ == "__main__":
    main()
