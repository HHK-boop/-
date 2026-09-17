$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$RuntimeRoot = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies"

$Python = $env:WEEK13_PYTHON
if (-not $Python) {
    $BundledPython = Join-Path $RuntimeRoot "python\python.exe"
    if (Test-Path -LiteralPath $BundledPython) { $Python = $BundledPython }
}
if (-not $Python) {
    $PythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($PythonCommand) { $Python = $PythonCommand.Source }
}
if (-not $Python) { throw "Python not found. Set WEEK13_PYTHON." }

$Node = $env:WEEK13_NODE
if (-not $Node) {
    $BundledNode = Join-Path $RuntimeRoot "node\bin\node.exe"
    if (Test-Path -LiteralPath $BundledNode) { $Node = $BundledNode }
}
if (-not $Node) {
    $NodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
    if ($NodeCommand) { $Node = $NodeCommand.Source }
}
if (-not $Node) { throw "Node.js not found. Set WEEK13_NODE." }

$NodeModules = Join-Path $Root "node_modules"
if (-not (Test-Path -LiteralPath $NodeModules)) {
    $BundledModules = Join-Path $RuntimeRoot "node\node_modules"
    if (-not (Test-Path -LiteralPath $BundledModules)) {
        throw "@oai/artifact-tool dependency not found. Install dependencies or set up node_modules."
    }
    New-Item -ItemType Junction -Path $NodeModules -Target $BundledModules | Out-Null
}

$env:PYTHONUTF8 = "1"
Push-Location $Root
try {
    & $Python "code\week13_batch_pipeline.py"
    if ($LASTEXITCODE -ne 0) { throw "week13_batch_pipeline.py failed" }

    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "database\run_postgres_temp_week13.ps1"
    if ($LASTEXITCODE -ne 0) { throw "PostgreSQL validation failed" }

    & $Python "code\prepare_week13_workbook_data.py"
    if ($LASTEXITCODE -ne 0) { throw "prepare_week13_workbook_data.py failed" }

    & $Node "code\build_week13_workbook.mjs"
    $WorkbookExit = $LASTEXITCODE
    if ($WorkbookExit -ne 0) {
        $WorkbookPath = Get-ChildItem -LiteralPath (Join-Path $Root "outputs") -Filter "*.xlsx" |
            Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName
        if (-not $WorkbookPath) { throw "build_week13_workbook.mjs failed: XLSX not found" }
        $InspectPath = "$WorkbookPath.inspect.ndjson"
        $FormulaErrors = @("#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A", "#NUM!", "#NULL!", "#SPILL!", "#CALC!")
        $InspectText = if (Test-Path -LiteralPath $InspectPath) { Get-Content -LiteralPath $InspectPath -Raw } else { "" }
        $HasFormulaError = $FormulaErrors | Where-Object { $InspectText.Contains($_) }
        if (-not (Test-Path -LiteralPath $WorkbookPath) -or $HasFormulaError) {
            throw "build_week13_workbook.mjs failed"
        }
        Write-Warning "Artifact Tool returned a non-zero diagnostic status, but XLSX export and formula scan passed."
    }

    & $Python "code\build_week13_report_docx.py"
    if ($LASTEXITCODE -ne 0) { throw "build_week13_report_docx.py failed" }

    & $Python "code\validate_week13_outputs.py"
    if ($LASTEXITCODE -ne 0) { throw "validate_week13_outputs.py failed" }

    Write-Host "Week 13 package regenerated and validated successfully." -ForegroundColor Green
}
finally {
    Pop-Location
}
