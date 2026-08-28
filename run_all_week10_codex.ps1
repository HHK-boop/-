$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = "C:\Users\29818\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$Node = "C:\Users\29818\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
$NodeModules = "C:\Users\29818\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules"
$ProjectNodeModules = Join-Path $Root "node_modules"

Push-Location $Root
try {
    if ((Test-Path -LiteralPath $NodeModules) -and -not (Test-Path -LiteralPath $ProjectNodeModules)) {
        cmd /c mklink /J "$ProjectNodeModules" "$NodeModules" | Out-Null
    }

    & $Python code\week10_analysis_pipeline.py
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File database\run_postgres_temp_week10.ps1
    & $Python code\week10_analysis_pipeline.py
    & $Node code\build_week10_workbook.mjs
    & $Python code\build_week10_report_docx.py
    & $Python code\build_week10_report_pdf.py
}
finally {
    Pop-Location
}
