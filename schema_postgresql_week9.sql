-- Week 9 PE/VC prospectus structured data schema
CREATE SCHEMA IF NOT EXISTS pevc_week9;

DROP TABLE IF EXISTS pevc_week9.company_dim CASCADE;
CREATE TABLE pevc_week9.company_dim (
    stock_code text PRIMARY KEY,
    company_short text,
    market text,
    subscription_records integer,
    snapshot_records integer,
    transfer_records integer,
    total_records integer,
    week8_p1_items integer,
    week9_closed_items integer,
    week9_unresolved_p1_items integer
);

DROP TABLE IF EXISTS pevc_week9.review_queue_resolved CASCADE;
CREATE TABLE pevc_week9.review_queue_resolved (
    queue_id text PRIMARY KEY,
    stock_code text,
    company_short text,
    market text,
    source text,
    issue_type text,
    week8_status text,
    week9_resolution text,
    data_action text,
    analysis_action text,
    evidence_principle text,
    remaining_risk text
);

DROP TABLE IF EXISTS pevc_week9.research_variables CASCADE;
CREATE TABLE pevc_week9.research_variables (
    stock_code text PRIMARY KEY,
    company_short text,
    market text,
    has_vc_or_pe integer,
    vc_record_count integer,
    pe_record_count integer,
    broad_pevc_record_count integer,
    broad_pevc_record_share numeric,
    pevc_intensity_level text,
    distinct_investor_type_count integer,
    transfer_event_count integer,
    week8_p1_item_count integer,
    week9_closed_p1_count integer,
    week9_unresolved_p1_count integer,
    top1_ratio_pct numeric,
    top3_ratio_pct numeric,
    hhi numeric,
    effective_shareholder_count numeric,
    broad_pevc_holder_count integer,
    broad_pevc_ratio_sum_pct numeric,
    dispersion_level text,
    week9_research_note text
);

DROP TABLE IF EXISTS pevc_week9.board_stats CASCADE;
CREATE TABLE pevc_week9.board_stats (
    market text PRIMARY KEY,
    company_count integer,
    vc_pe_supported_count integer,
    avg_broad_pevc_record_share numeric,
    avg_distinct_investor_type_count numeric,
    avg_top1_ratio_pct numeric,
    avg_effective_shareholder_count numeric,
    week9_interpretation text
);

DROP TABLE IF EXISTS pevc_week9.ownership_metrics CASCADE;
CREATE TABLE pevc_week9.ownership_metrics (
    stock_code text PRIMARY KEY,
    company_short text,
    market text,
    selected_time_point text,
    shareholder_count integer,
    top1_ratio_pct numeric,
    top3_ratio_pct numeric,
    hhi numeric,
    effective_shareholder_count numeric,
    broad_pevc_holder_count integer,
    broad_pevc_ratio_sum_pct numeric,
    dispersion_level text,
    analysis_note text
);
