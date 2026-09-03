-- Week 11 PostgreSQL import script. Run with psql from the submission root.
SET client_encoding = 'UTF8';
SET search_path TO pevc_week11;

\copy "week11_database_migration_plan" FROM 'data/derived/week11_database_migration_plan.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy "week11_persistent_db_readiness" FROM 'data/derived/week11_persistent_db_readiness.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy "week11_fund_deep_enrichment_queue" FROM 'data/derived/week11_fund_deep_enrichment_queue.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy "week11_manual_verification_template" FROM 'data/derived/week11_manual_verification_template.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy "week11_research_design_matrix" FROM 'data/derived/week11_research_design_matrix.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy "week11_variable_dictionary" FROM 'data/derived/week11_variable_dictionary.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy "week11_sample_expansion_plan" FROM 'data/derived/week11_sample_expansion_plan.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy "week11_quality_dashboard" FROM 'data/derived/week11_quality_dashboard.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy "week11_completion_checklist" FROM 'data/derived/week11_completion_checklist.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy "week11_manifest" FROM 'data/derived/week11_manifest.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
