-- Week 7 PostgreSQL schema draft for PE/VC IPO prospectus three-table data
-- Author: Huo Hongkun
-- Principle: Final data keeps PDF-undisclosed numeric fields as NULL, not 0.

CREATE TABLE IF NOT EXISTS companies (
    stock_code TEXT PRIMARY KEY,
    company_short TEXT NOT NULL,
    market TEXT,
    week7_scope TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS investors (
    investor_id BIGSERIAL PRIMARY KEY,
    investor_name TEXT NOT NULL,
    investor_type_final TEXT,
    investor_type_method TEXT,
    investor_type_reason TEXT,
    UNIQUE (investor_name, investor_type_final)
);

CREATE TABLE IF NOT EXISTS subscription_events (
    record_id TEXT PRIMARY KEY,
    stock_code TEXT REFERENCES companies(stock_code),
    event_date TEXT,
    batch_label TEXT,
    subscriber_name TEXT,
    investor_type_final TEXT,
    subscription_shares_wan NUMERIC,
    subscription_amount_wan NUMERIC,
    subscription_price_yuan NUMERIC,
    computed_price_yuan NUMERIC,
    subscription_ratio_pct NUMERIC,
    currency TEXT,
    pdf_page TEXT,
    source_evidence TEXT,
    final_status TEXT,
    final_note TEXT
);

CREATE TABLE IF NOT EXISTS equity_snapshots (
    record_id TEXT PRIMARY KEY,
    stock_code TEXT REFERENCES companies(stock_code),
    time_point TEXT,
    equity_structure_scope TEXT,
    shareholder_name TEXT,
    investor_type_final TEXT,
    shares_held_wan NUMERIC,
    capital_contribution_wan NUMERIC,
    shareholding_ratio_pct NUMERIC,
    total_shares_wan NUMERIC,
    total_capital_wan NUMERIC,
    pdf_page TEXT,
    source_evidence TEXT,
    final_status TEXT,
    final_note TEXT
);

CREATE TABLE IF NOT EXISTS transfer_events (
    record_id TEXT PRIMARY KEY,
    stock_code TEXT REFERENCES companies(stock_code),
    transfer_date TEXT,
    batch_label TEXT,
    transferor_name TEXT,
    transferor_type_final TEXT,
    transferee_name TEXT,
    transferee_type_final TEXT,
    transferred_shares_wan NUMERIC,
    transfer_amount_wan NUMERIC,
    transfer_price_yuan NUMERIC,
    transfer_ratio_pct NUMERIC,
    pdf_page TEXT,
    source_evidence TEXT,
    final_status TEXT,
    final_note TEXT
);

CREATE TABLE IF NOT EXISTS validation_results (
    validation_id BIGSERIAL PRIMARY KEY,
    check_type TEXT,
    stock_code TEXT,
    record_id TEXT,
    status TEXT,
    metric NUMERIC,
    detail TEXT,
    week7_action TEXT
);
