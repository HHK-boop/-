SET client_min_messages TO warning;
CREATE SCHEMA IF NOT EXISTS pevc_week13;
SET search_path TO pevc_week13;

DROP TABLE IF EXISTS week13_selected_companies;
CREATE TABLE week13_selected_companies (
  batch_order text, queue_id text, stock_code text, company_short text, board text,
  source_platform text, source_url text, original_text_path text, package_text_file text,
  page_count text, week12_keyword_hits text, selection_reason text, missing_policy text
);

DROP TABLE IF EXISTS week13_chapter_locator;
CREATE TABLE week13_chapter_locator (
  stock_code text, company_short text, chapter_group text, located text,
  first_page text, top_pages text, matched_terms text, hit_pages_count text
);

DROP TABLE IF EXISTS week13_auto_evidence_candidates;
CREATE TABLE week13_auto_evidence_candidates (
  candidate_id text, stock_code text, company_short text, event_code text, event_type text,
  source_page text, matched_term text, term_hit_count text, date_text text, amount_text text,
  shares_text text, ratio_text text, investor_candidate_count text, confidence text,
  auto_status text, exclusion_reason text, evidence_excerpt text, source_url text,
  local_text_file text, gold_final_value text, review_note text
);

DROP TABLE IF EXISTS week13_investor_profile;
CREATE TABLE week13_investor_profile (
  profile_id text, stock_code text, company_short text, investor_name_candidate text,
  investor_type_candidate text, is_pevc_candidate text, classification_basis text,
  evidence_pages text, occurrence_count text, manual_review_status text,
  amac_filing_code text, gp_name text, lp_structure text, deep_field_rule text
);

DROP TABLE IF EXISTS week13_investor_type_rules;
CREATE TABLE week13_investor_type_rules (
  type text, positive_rule text, negative_rule text, final_requirement text
);

DROP TABLE IF EXISTS week13_event_summary;
CREATE TABLE week13_event_summary (
  event_code text, event_type text, candidate_records text, companies_covered text,
  high_confidence_records text, with_date text, with_amount_or_shares text, use_note text
);

DROP TABLE IF EXISTS week13_old_new_crosscheck;
CREATE TABLE week13_old_new_crosscheck (
  stock_code text, company_short text, old_candidate_record_count text,
  old_unique_pages text, week13_retained_records text, week13_unique_pages text,
  overlap_pages text, old_page_recovery_rate text, newly_located_pages text,
  comparison_scope text
);

DROP TABLE IF EXISTS week13_company_progress;
CREATE TABLE week13_company_progress (
  stock_code text, company_short text, page_count text, chapter_groups_located text,
  retained_auto_candidates text, excluded_transfer_boilerplate text,
  investor_name_candidates text, high_confidence_candidates text, processing_status text
);

DROP TABLE IF EXISTS week13_manual_review_queue;
CREATE TABLE week13_manual_review_queue (
  review_id text, priority text, candidate_id text, stock_code text, company_short text,
  event_type text, source_page text, confidence text, review_reason text,
  human_decision text, corrected_value text, reviewer text, review_date text,
  evidence_excerpt text
);

DROP TABLE IF EXISTS week13_weekly_plan;
CREATE TABLE week13_weekly_plan (
  day text, task text, action text, output text, status text
);

DROP TABLE IF EXISTS week13_validation_summary;
CREATE TABLE week13_validation_summary (
  check_item text, status text, value text, rule text
);
