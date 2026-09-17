$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$PgBin = $env:WEEK13_PGBIN
if (-not $PgBin) {
    $psqlCommand = Get-Command psql.exe -ErrorAction SilentlyContinue
    if ($psqlCommand) { $PgBin = Split-Path -Parent $psqlCommand.Source }
}
if (-not $PgBin) {
    $postgresRoot = Join-Path $env:ProgramFiles "PostgreSQL"
    if (Test-Path -LiteralPath $postgresRoot) {
        $PgBin = Get-ChildItem -LiteralPath $postgresRoot -Directory |
            Sort-Object { [int](($_.Name -split '\.')[0] -replace '[^0-9]', '') } -Descending |
            ForEach-Object { Join-Path $_.FullName "bin" } |
            Where-Object { Test-Path -LiteralPath (Join-Path $_ "psql.exe") } |
            Select-Object -First 1
    }
}
if (-not $PgBin) { throw "PostgreSQL bin directory not found. Set WEEK13_PGBIN or add psql.exe to PATH." }
$InitDb = Join-Path $PgBin "initdb.exe"
$PgCtl = Join-Path $PgBin "pg_ctl.exe"
$Psql = Join-Path $PgBin "psql.exe"
$PgReady = Join-Path $PgBin "pg_isready.exe"
$Postgres = Join-Path $PgBin "postgres.exe"
$Port = if ($env:WEEK13_PGPORT) { $env:WEEK13_PGPORT } else { "55435" }
$RuntimeRoot = Join-Path $env:TEMP "hhk_week13_postgresql_runtime_utf8"
$DataDir = Join-Path $RuntimeRoot "data"
$LogDir = Join-Path $Root "logs"
$ServerOutLog = Join-Path $LogDir "postgresql_temp_server_stdout_week13.log"
$ServerErrLog = Join-Path $LogDir "postgresql_temp_server_stderr_week13.log"
$RunLog = Join-Path $LogDir "postgresql_temp_run_week13.log"

New-Item -ItemType Directory -Force -Path $RuntimeRoot, $LogDir | Out-Null

foreach ($tool in @($InitDb, $PgCtl, $Psql, $PgReady, $Postgres)) {
    if (-not (Test-Path -LiteralPath $tool)) { throw "PostgreSQL tool not found: $tool" }
}

function Invoke-LoggedExternal {
    param([string]$Exe, [string[]]$Arguments, [string]$StepName, [string]$LogPath)
    $output = & $Exe @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    if ($output) { $output | Add-Content -LiteralPath $LogPath -Encoding UTF8 }
    "step=$StepName exit_code=$exitCode" | Add-Content -LiteralPath $LogPath -Encoding UTF8
    if ($exitCode -ne 0) { throw "$StepName failed with exit code $exitCode" }
}

Push-Location $Root
$started = $false
try {
    "run_time=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Set-Content -LiteralPath $RunLog -Encoding UTF8
    "port=$Port" | Add-Content -LiteralPath $RunLog -Encoding UTF8
    if (-not (Test-Path -LiteralPath (Join-Path $DataDir "PG_VERSION"))) {
        Invoke-LoggedExternal -Exe $InitDb -Arguments @("-D", $DataDir, "-U", "postgres", "-A", "trust", "-E", "UTF8", "--locale=C") -StepName "initdb" -LogPath $RunLog
    }
    & $PgReady -h 127.0.0.1 -p $Port *> $null
    if ($LASTEXITCODE -ne 0) {
        $process = Start-Process -FilePath $Postgres -ArgumentList @("-D", $DataDir, "-p", $Port, "-c", "listen_addresses=127.0.0.1") -RedirectStandardOutput $ServerOutLog -RedirectStandardError $ServerErrLog -WindowStyle Hidden -PassThru
        $started = $true
        "postgres_pid=$($process.Id)" | Add-Content -LiteralPath $RunLog -Encoding UTF8
        $ready = $false
        for ($i = 0; $i -lt 30; $i++) {
            Start-Sleep -Seconds 1
            & $PgReady -h 127.0.0.1 -p $Port *> $null
            if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        }
        if (-not $ready) { throw "Temporary PostgreSQL server did not become ready on port $Port" }
    }
    Invoke-LoggedExternal -Exe $Psql -Arguments @("-h", "127.0.0.1", "-p", $Port, "-U", "postgres", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-f", "database\schema_postgresql_week13.sql") -StepName "schema" -LogPath $RunLog
    Invoke-LoggedExternal -Exe $Psql -Arguments @("-h", "127.0.0.1", "-p", $Port, "-U", "postgres", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-f", "database\import_week13_tables.sql") -StepName "import" -LogPath $RunLog
    Invoke-LoggedExternal -Exe $Psql -Arguments @("-h", "127.0.0.1", "-p", $Port, "-U", "postgres", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-f", "database\postgres_week13_queries.sql") -StepName "queries" -LogPath $RunLog
}
finally {
    if ($started) {
        & $PgCtl -D $DataDir stop -m fast 2>&1 | Add-Content -LiteralPath $RunLog -Encoding UTF8
    }
    Pop-Location
}
