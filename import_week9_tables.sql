\set ON_ERROR_STOP on
\i database/schema_postgresql_week9.sql
\copy pevc_week9.company_dim FROM 'data/derived/company_dim_week9.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy pevc_week9.review_queue_resolved FROM 'review/review_queue_resolved_week9.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy pevc_week9.research_variables FROM 'data/derived/research_variables_week9.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy pevc_week9.board_stats FROM 'data/derived/board_stats_week9.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy pevc_week9.ownership_metrics FROM 'data/derived/ownership_metrics_week9.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

SELECT 'company_dim' AS table_name, count(*) AS rows FROM pevc_week9.company_dim
UNION ALL SELECT 'review_queue_resolved', count(*) FROM pevc_week9.review_queue_resolved
UNION ALL SELECT 'research_variables', count(*) FROM pevc_week9.research_variables
UNION ALL SELECT 'board_stats', count(*) FROM pevc_week9.board_stats
UNION ALL SELECT 'ownership_metrics', count(*) FROM pevc_week9.ownership_metrics;
