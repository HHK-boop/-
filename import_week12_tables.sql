-- Week 12 PostgreSQL import script. Run with psql from the submission root.
SET client_encoding = 'UTF8';
SET search_path TO pevc_week12;

\copy "week12_source_catalog" FROM 'data/derived/week12_source_catalog.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy "week12_source_inventory" FROM 'data/derived/week12_source_inventory.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy "week12_expanded_company_universe" FROM 'data/derived/week12_expanded_company_universe.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy "week12_processing_queue" FROM 'data/derived/week12_processing_queue.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy "week12_source_summary" FROM 'data/derived/week12_source_summary.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy "week12_board_coverage_summary" FROM 'data/derived/week12_board_coverage_summary.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy "week12_field_source_matrix" FROM 'data/derived/week12_field_source_matrix.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy "week12_weekly_plan" FROM 'data/derived/week12_weekly_plan.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy "week12_scaling_protocol" FROM 'data/derived/week12_scaling_protocol.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy "week12_quality_gates" FROM 'data/derived/week12_quality_gates.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy "week12_database_load_plan" FROM 'data/derived/week12_database_load_plan.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy "week12_submission_checklist" FROM 'data/derived/week12_submission_checklist.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
