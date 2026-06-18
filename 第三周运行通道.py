from __future__ import annotations

import subprocess
import sys
import shutil
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SCRIPTS = [
    "code/01_build_company_list/build_week3_bse_company_list.js",
    "code/03_download_pdfs/prepare_week3_pdfs.py",
    "code/04_parse_pdf_to_markdown/parse_week3_pdfs.py",
    "code/05_locate_relevant_sections/locate_week3_sections.py",
    "code/06_extract_pevc_info/extract_week3_pevc_info.py",
    "code/07_validate_outputs/validate_week3_outputs.py",
    "code/07_validate_outputs/build_week3_report_and_review.py",
    "code/07_validate_outputs/render_week3_report_docx.py",
    "code/07_validate_outputs/build_week3_detailed_report.py",
]


def node_executable() -> str:
    node = shutil.which("node")
    if node:
        return node
    bundled = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "node" / "bin" / "node.exe"
    if bundled.exists():
        return str(bundled)
    raise RuntimeError("Node.js is required for the BSE company-list scraper. Please install Node.js or run with the Codex bundled runtime.")


def main() -> None:
    node = node_executable()
    for script in SCRIPTS:
        print(f"Running {script}")
        if script.endswith(".js"):
            command = [node, str(ROOT / script)]
            env = os.environ.copy()
            bundled_modules = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "node" / "node_modules"
            bundled_pnpm_modules = bundled_modules / ".pnpm" / "node_modules"
            extra_paths = [str(path) for path in [bundled_modules, bundled_pnpm_modules] if path.exists()]
            if extra_paths:
                env["NODE_PATH"] = os.pathsep.join(extra_paths + ([env["NODE_PATH"]] if env.get("NODE_PATH") else []))
        else:
            command = [sys.executable, str(ROOT / script)]
            env = None
        subprocess.run(command, check=True, cwd=ROOT, env=env)


if __name__ == "__main__":
    main()
