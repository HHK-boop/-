# PostgreSQL导入计划

## 一、导入顺序

1. `companies_week7_manifest.csv` -> `companies`
2. `subscription_week7_final.csv` -> `subscription_events`
3. `equity_snapshot_week7_final.csv` -> `equity_snapshots`
4. `transfer_week7_final.csv` -> `transfer_events`
5. `week7_issue_log.csv` -> `validation_results`

## 二、注意事项

- 数值字段中的空值导入为 `NULL`，不替换为0。
- `stock_code` 按6位文本保存，避免 `001282` 被Excel或数据库转成 `1282`。
- `pdf_page` 保持文本格式，因为北交所招股书常见 `1-1-48` 这类页码。
- `source_evidence` 作为证据字段保留，后续可拆出独立证据表。
- 先做单机导入测试，再接入更大样本。

## 三、后续测试SQL

```sql
SELECT market, COUNT(DISTINCT stock_code) AS company_count
FROM companies
GROUP BY market;

SELECT investor_type_final, COUNT(*) AS records
FROM (
    SELECT investor_type_final FROM subscription_events
    UNION ALL
    SELECT investor_type_final FROM equity_snapshots
) t
GROUP BY investor_type_final
ORDER BY records DESC;

SELECT status, COUNT(*) AS records
FROM validation_results
GROUP BY status;
```
