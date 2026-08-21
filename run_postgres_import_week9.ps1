$ErrorActionPreference = 'Stop'
$Psql = 'C:\Program Files\PostgreSQL\18\bin\psql.exe'
if (!(Test-Path $Psql)) { $Psql = 'psql' }
# 使用前请先设置环境变量：$env:PGPASSWORD='你的PostgreSQL密码'
& $Psql -h localhost -p 5432 -U postgres -d postgres -f database\import_week9_tables.sql
