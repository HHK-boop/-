-- Week 10 PostgreSQL import script. Run with psql from the submission root.
SET client_encoding = 'UTF8';

\copy company_research_panel_week10 FROM 'data/derived/company_research_panel_week10.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy investor_profile_week10 FROM 'data/derived/investor_profile_week10.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy fund_enrichment_queue_week10 FROM 'data/derived/fund_enrichment_queue_week10.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy descriptive_stats_week10 FROM 'data/derived/descriptive_stats_week10.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy board_stats_week10 FROM 'data/derived/board_stats_week10.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy correlation_matrix_week10 FROM 'data/derived/correlation_matrix_week10.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy regression_results_week10 FROM 'data/derived/regression_results_week10.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy research_questions_week10 FROM 'data/derived/research_questions_week10.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy data_quality_gate_week10 FROM 'data/derived/data_quality_gate_week10.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy field_completeness_week10 FROM 'data/derived/field_completeness_week10.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');