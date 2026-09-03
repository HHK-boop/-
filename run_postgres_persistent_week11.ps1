$ErrorActionPreference = "Stop"

param(
    [string]$HostName = "127.0.0.1",
    [string]$Port = "5432",
    [string]$User = "postgres",
    [string]$Database = "postgres"
)

$Root = Split-Path -Parent $PSScriptRoot
$PgBin = "C:\Program Files\PostgreSQL\18\bin"
$Psql = Join-Path $PgBin "psql.exe"
$PgReady = Join-Path $PgBin "pg_isready.exe"
$RunLog = Join-Path $Root "logs\postgresql_persistent_run_week11.log"

New-Item -ItemType Directory -Force -Path (Join-Path $Root "logs") | Out-Null
"run_time=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Set-Content -LiteralPath $RunLog -Encoding UTF8

if (-not (Test-Path -LiteralPath $Psql)) {
    throw "psql.exe not found: $Psql"
}
if (-not $env:PGPASSWORD) {
    throw "PGPASSWORD is not set. Set it first, then rerun this script."
}

Push-Location $Root
try {
    & $PgReady -h $HostName -p $Port | Add-Content -LiteralPath $RunLog -Encoding UTF8
    if ($LASTEXITCODE -ne 0) {
        throw "PostgreSQL is not ready on $HostName`:$Port"
    }
    & $Psql -h $HostName -p $Port -U $User -d $Database -v ON_ERROR_STOP=1 -f "database\schema_postgresql_week11.sql" 2>&1 | Add-Content -LiteralPath $RunLog -Encoding UTF8
    if ($LASTEXITCODE -ne 0) { throw "schema import failed" }
    & $Psql -h $HostName -p $Port -U $User -d $Database -v ON_ERROR_STOP=1 -f "database\import_week11_tables.sql" 2>&1 | Add-Content -LiteralPath $RunLog -Encoding UTF8
    if ($LASTEXITCODE -ne 0) { throw "csv import failed" }
    & $Psql -h $HostName -p $Port -U $User -d $Database -v ON_ERROR_STOP=1 -f "database\postgres_week11_queries.sql" 2>&1 | Add-Content -LiteralPath $RunLog -Encoding UTF8
    if ($LASTEXITCODE -ne 0) { throw "disclosure query failed" }
}
finally {
    Pop-Location
}
