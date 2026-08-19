-- Run from the Week 8 submission root folder in psql.
-- Example:
-- psql -d pevc -f database/schema_postgresql_week8.sql
-- psql -d pevc -f database/import_week8_derived_tables.sql

\copy week8_company_summary FROM 'data/derived/company_summary_week8.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy week8_quality_metrics FROM 'data/derived/quality_metrics_week8.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy week8_review_queue FROM 'review/week8_review_queue.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy week8_research_variables FROM 'data/derived/research_variables_week8.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
