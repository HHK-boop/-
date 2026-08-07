# PostgreSQL导入测试记录

姓名：霍泓锟  
日期：2026-08-01

## 一、本机环境检查

已在本机发现 PostgreSQL 命令行工具：

```text
C:\Program Files\PostgreSQL\18\bin\psql.exe
psql (PostgreSQL) 18.4
```

## 二、本周完成情况

本周已完成数据库化前的表结构准备：

- `schema_postgresql.sql`：公司表、投资主体表、认缴事件表、股权快照表、股权转让表、验证结果表。
- `import_plan.md`：导入顺序、字段注意事项和测试SQL。
- `data/*.csv`：可导入数据库的 Week7 版三表与辅助表。

## 三、尚未直接导入的原因

当前任务环境中没有明确的 PostgreSQL 用户名、密码和目标数据库名。为避免在未授权数据库中创建表，本周先完成可复现表结构和导入说明。后续拿到数据库连接信息后，可按以下顺序执行。

## 四、后续导入命令示例

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d pevc_week7 -f "database/schema_postgresql.sql"
```

导入 CSV 时需注意：

- `stock_code` 使用文本字段，避免 `001282` 变成 `1282`。
- 空值导入为 `NULL`，不能替换为 0。
- `pdf_page` 使用文本字段，兼容 `1-1-48` 这类页码。
