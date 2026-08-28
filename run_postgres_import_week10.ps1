$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Psql = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
if (!(Test-Path $Psql)) {
  $Psql = "psql"
}
if (-not $env:PGPASSWORD) {
  Write-Host "请先设置本机PostgreSQL密码，例如：$env:PGPASSWORD='你的密码'"
  exit 1
}
Push-Location $Root
& $Psql -h localhost -p 5432 -U postgres -d postgres -f "database/schema_postgresql_week10.sql"
& $Psql -h localhost -p 5432 -U postgres -d postgres -f "database/import_week10_tables.sql"
Pop-Location
