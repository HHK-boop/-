-- Week 8 PostgreSQL schema extension for PE/VC prospectus data
-- Author: Huo Hongkun
-- Principle: PDF-undisclosed values remain NULL, not 0.

CREATE TABLE IF NOT EXISTS week8_company_summary (
    stock_code TEXT PRIMARY KEY,
    company_short TEXT NOT NULL,
    market TEXT,
    subscription_records INTEGER,
    snapshot_records INTEGER,
    transfer_records INTEGER,
    total_records INTEGER,
    broad_pevc_records INTEGER,
    pdf_page_coverage NUMERIC,
    evidence_coverage NUMERIC
);

CREATE TABLE IF NOT EXISTS week8_quality_metrics (
    table_name TEXT PRIMARY KEY,
    total_records INTEGER,
    pdf_page_coverage NUMERIC,
    evidence_coverage NUMERIC,
    investor_type_coverage NUMERIC,
    review_queue_items INTEGER,
    quality_note TEXT
);

CREATE TABLE IF NOT EXISTS week8_review_queue (
    queue_id TEXT PRIMARY KEY,
    stock_code TEXT,
    company_short TEXT,
    source TEXT,
    issue_type TEXT,
    status TEXT,
    detail TEXT,
    suggested_action TEXT
);

CREATE TABLE IF NOT EXISTS week8_research_variables (
    stock_code TEXT PRIMARY KEY,
    company_short TEXT,
    market TEXT,
    has_vc_or_pe INTEGER,
    vc_record_count INTEGER,
    pe_record_count INTEGER,
    broad_pevc_record_count INTEGER,
    broad_pevc_record_share NUMERIC,
    natural_person_record_share NUMERIC,
    distinct_investor_type_count INTEGER,
    transfer_event_count INTEGER,
    p1_review_item_count INTEGER,
    research_use_note TEXT
);
