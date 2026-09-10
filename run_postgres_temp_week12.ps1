$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$PgBin = "C:\Program Files\PostgreSQL\18\bin"
$InitDb = Join-Path $PgBin "initdb.exe"
$PgCtl = Join-Path $PgBin "pg_ctl.exe"
$Psql = Join-Path $PgBin "psql.exe"
$PgReady = Join-Path $PgBin "pg_isready.exe"
$Postgres = Join-Path $PgBin "postgres.exe"
$Port = if ($env:WEEK12_PGPORT) { $env:WEEK12_PGPORT } else { "55434" }
$RuntimeRoot = Join-Path $env:TEMP "hhk_week12_postgresql_runtime_utf8"
$DataDir = Join-Path $RuntimeRoot "data"
$LogDir = Join-Path $Root "logs"
$ServerOutLog = Join-Path $LogDir "postgresql_temp_server_stdout_week12.log"
$ServerErrLog = Join-Path $LogDir "postgresql_temp_server_stderr_week12.log"
$RunLog = Join-Path $LogDir "postgresql_temp_run_week12.log"

New-Item -ItemType Directory -Force -Path $RuntimeRoot, $LogDir | Out-Null

foreach ($tool in @($InitDb, $PgCtl, $Psql, $PgReady, $Postgres)) {
    if (-not (Test-Path -LiteralPath $tool)) {
        throw "PostgreSQL tool not found: $tool"
    }
}

function Invoke-LoggedExternal {
    param(
        [string]$Exe,
        [string[]]$Arguments,
        [string]$StepName,
        [string]$LogPath
    )
    $output = & $Exe @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    if ($output) {
        $output | Add-Content -LiteralPath $LogPath -Encoding UTF8
    }
    "step=$StepName exit_code=$exitCode" | Add-Content -LiteralPath $LogPath -Encoding UTF8
    if ($exitCode -ne 0) {
        throw "$StepName failed with exit code $exitCode"
    }
}

Push-Location $Root
try {
    "run_time=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Set-Content -LiteralPath $RunLog -Encoding UTF8
    "runtime_root=$RuntimeRoot" | Add-Content -LiteralPath $RunLog -Encoding UTF8
    "port=$Port" | Add-Content -LiteralPath $RunLog -Encoding UTF8

    if (-not (Test-Path -LiteralPath (Join-Path $DataDir "PG_VERSION"))) {
        Invoke-LoggedExternal -Exe $InitDb -Arguments @("-D", $DataDir, "-U", "postgres", "-A", "trust", "-E", "UTF8", "--locale=C") -StepName "initdb" -LogPath $RunLog
    }

    $serverStartedByThisScript = $false
    & $PgReady -h 127.0.0.1 -p $Port *> $null
    if ($LASTEXITCODE -ne 0) {
        $serverProcess = Start-Process -FilePath $Postgres -ArgumentList @("-D", $DataDir, "-p", $Port, "-c", "listen_addresses=127.0.0.1") -RedirectStandardOutput $ServerOutLog -RedirectStandardError $ServerErrLog -WindowStyle Hidden -PassThru
        $serverStartedByThisScript = $true
        "postgres_pid=$($serverProcess.Id)" | Add-Content -LiteralPath $RunLog -Encoding UTF8
        $ready = $false
        for ($i = 0; $i -lt 30; $i++) {
            Start-Sleep -Seconds 1
            & $PgReady -h 127.0.0.1 -p $Port *> $null
            if ($LASTEXITCODE -eq 0) {
                $ready = $true
                break
            }
        }
        if (-not $ready) {
            throw "Temporary PostgreSQL server did not become ready on port $Port"
        }
    }

    & $PgReady -h 127.0.0.1 -p $Port | Add-Content -LiteralPath $RunLog -Encoding UTF8
    Invoke-LoggedExternal -Exe $Psql -Arguments @("-h", "127.0.0.1", "-p", $Port, "-U", "postgres", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-f", "database\schema_postgresql_week12.sql") -StepName "schema" -LogPath $RunLog
    Invoke-LoggedExternal -Exe $Psql -Arguments @("-h", "127.0.0.1", "-p", $Port, "-U", "postgres", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-f", "database\import_week12_tables.sql") -StepName "import" -LogPath $RunLog
    Invoke-LoggedExternal -Exe $Psql -Arguments @("-h", "127.0.0.1", "-p", $Port, "-U", "postgres", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-f", "database\postgres_week12_queries.sql") -StepName "queries" -LogPath $RunLog
    Invoke-LoggedExternal -Exe $Psql -Arguments @("-h", "127.0.0.1", "-p", $Port, "-U", "postgres", "-d", "postgres", "-At", "-c", "select 'postgres_temp_import_status=PASS';") -StepName "status_query" -LogPath $RunLog

    if ($serverStartedByThisScript) {
        Invoke-LoggedExternal -Exe $PgCtl -Arguments @("-D", $DataDir, "stop", "-m", "fast") -StepName "stop" -LogPath $RunLog
    }
}
finally {
    Pop-Location
}
