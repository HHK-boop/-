-- Week 10 PostgreSQL schema generated from derived CSV files.
-- Run from the submission root. Use UTF-8 client encoding.
SET client_encoding = 'UTF8';

DROP TABLE IF EXISTS company_research_panel_week10;
CREATE TABLE company_research_panel_week10 (
    "stock_code" text,
    "company_short" text,
    "market" text,
    "has_vc_or_pe" numeric,
    "vc_record_count" numeric,
    "pe_record_count" numeric,
    "broad_pevc_record_count" numeric,
    "broad_pevc_record_share" numeric,
    "pevc_intensity_level" text,
    "distinct_investor_type_count" numeric,
    "transfer_event_count" numeric,
    "week8_p1_item_count" numeric,
    "week9_closed_p1_count" numeric,
    "week9_unresolved_p1_count" numeric,
    "top1_ratio_pct" numeric,
    "top3_ratio_pct" numeric,
    "hhi" numeric,
    "effective_shareholder_count" numeric,
    "broad_pevc_holder_count" numeric,
    "broad_pevc_ratio_sum_pct" numeric,
    "dispersion_level" text,
    "week9_research_note" text,
    "pevc_record_share_decimal" numeric,
    "broad_pevc_ratio_decimal" numeric,
    "top1_ratio_decimal" numeric,
    "hhi_percent" numeric,
    "pevc_strength_index" numeric,
    "pre_ipo_dispersion_index" numeric,
    "pevc_strength_z" numeric,
    "dispersion_z" numeric,
    "caution_flag" numeric,
    "analysis_sample_flag" numeric,
    "board_group" text,
    "is_主板" numeric,
    "is_创业板" numeric,
    "is_科创板" numeric,
    "is_北交所" numeric,
    "invalid_ratio_timepoints" numeric,
    "blank_ratio_timepoints" numeric,
    "usable_ratio_timepoints" numeric,
    "quality_gate" text
);

DROP TABLE IF EXISTS investor_profile_week10;
CREATE TABLE investor_profile_week10 (
    "investor_name" text,
    "investor_type_final" text,
    "is_broad_pevc" numeric,
    "is_fund_like_name" numeric,
    "record_count" numeric,
    "company_count" numeric,
    "companies" text,
    "markets" text,
    "source_tables" text,
    "pdf_pages_observed" text,
    "manual_priority" text
);

DROP TABLE IF EXISTS fund_enrichment_queue_week10;
CREATE TABLE fund_enrichment_queue_week10 (
    "investor_name" text,
    "investor_type_final" text,
    "manual_priority" text,
    "company_count" numeric,
    "companies" text,
    "markets" text,
    "source_tables" text,
    "pdf_pages_observed" text,
    "amac_record_code" text,
    "gp_name" text,
    "lp_structure" text,
    "disclosure_status" text,
    "next_action" text,
    "week10_principle" text
);

DROP TABLE IF EXISTS descriptive_stats_week10;
CREATE TABLE descriptive_stats_week10 (
    "variable" text,
    "variable_label" text,
    "n" numeric,
    "mean" numeric,
    "median" numeric,
    "std" numeric,
    "min" numeric,
    "max" numeric,
    "interpretation" text
);

DROP TABLE IF EXISTS board_stats_week10;
CREATE TABLE board_stats_week10 (
    "market" text,
    "company_count" numeric,
    "avg_pevc_strength_index" numeric,
    "avg_broad_pevc_record_share" numeric,
    "avg_top1_ratio_pct" numeric,
    "avg_hhi" numeric,
    "avg_effective_shareholder_count" numeric,
    "caution_company_count" text,
    "week10_interpretation" text
);

DROP TABLE IF EXISTS correlation_matrix_week10;
CREATE TABLE correlation_matrix_week10 (
    "var_left" text,
    "var_right" text,
    "n" numeric,
    "pearson_corr" numeric,
    "note" text
);

DROP TABLE IF EXISTS regression_results_week10;
CREATE TABLE regression_results_week10 (
    "model_id" text,
    "sample_scope" text,
    "dependent_variable" text,
    "independent_variable" text,
    "n" numeric,
    "intercept" numeric,
    "coef_x" numeric,
    "std_error_x" numeric,
    "t_stat_x" numeric,
    "r_squared" numeric,
    "model_note" text
);

DROP TABLE IF EXISTS research_questions_week10;
CREATE TABLE research_questions_week10 (
    "question_id" text,
    "research_question" text,
    "current_evidence" text,
    "current_judgement" text,
    "next_data_need" text
);

DROP TABLE IF EXISTS data_quality_gate_week10;
CREATE TABLE data_quality_gate_week10 (
    "stock_code" text,
    "company_short" text,
    "market" text,
    "ratio_timepoints" numeric,
    "usable_ratio_timepoints" numeric,
    "invalid_ratio_timepoints" numeric,
    "abnormal_ratio_timepoints" numeric,
    "blank_ratio_timepoints" numeric,
    "week8_p1_count" numeric,
    "week9_closed_p1_count" numeric,
    "quality_gate" text,
    "quality_note" text
);

DROP TABLE IF EXISTS field_completeness_week10;
CREATE TABLE field_completeness_week10 (
    "table_name" text,
    "field_name" text,
    "record_count" numeric,
    "observed_count" numeric,
    "missing_count" numeric,
    "missing_rate" numeric,
    "week10_action" text
);
