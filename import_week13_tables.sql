SET client_encoding = 'UTF8';
SET search_path TO pevc_week13;

\copy week13_selected_companies FROM 'data/derived/week13_selected_companies.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy week13_chapter_locator FROM 'data/derived/week13_chapter_locator.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy week13_auto_evidence_candidates FROM 'data/derived/week13_auto_evidence_candidates.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy week13_investor_profile FROM 'data/derived/week13_investor_profile.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy week13_investor_type_rules FROM 'data/derived/week13_investor_type_rules.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy week13_event_summary FROM 'data/derived/week13_event_summary.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy week13_old_new_crosscheck FROM 'data/derived/week13_old_new_crosscheck.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy week13_company_progress FROM 'data/derived/week13_company_progress.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy week13_manual_review_queue FROM 'data/derived/week13_manual_review_queue.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy week13_weekly_plan FROM 'data/derived/week13_weekly_plan.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy week13_validation_summary FROM 'validation/week13_validation_summary.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
