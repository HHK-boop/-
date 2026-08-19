"""Create a clean zip package for the Week 8 submission."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
ZIP_PATH = ROOT.parent / f"{ROOT.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
SKIP_PREFIXES = {
    "node_modules",
    "report/rendered",
    "report/rendered_v2",
    "outputs/workbook_preview",
}


def should_skip(relative_path: str) -> bool:
    if relative_path.endswith(".inspect.ndjson"):
        return True
    return any(relative_path.startswith(prefix) for prefix in SKIP_PREFIXES)


def main() -> None:
    file_count = 0
    with ZipFile(ZIP_PATH, "w", ZIP_DEFLATED) as zf:
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT).as_posix()
            if should_skip(rel):
                continue
            zf.write(path, rel)
            file_count += 1
    print(f"Created: {ZIP_PATH}")
    print(f"Files: {file_count}")
    print(f"Bytes: {ZIP_PATH.stat().st_size}")


if __name__ == "__main__":
    main()
